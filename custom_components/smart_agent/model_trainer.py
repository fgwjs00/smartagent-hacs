"""
LocalModelTrainer — 本地个性化决策树训练器 (Phase P2: 本地 ML 快脑)。

每周从 training_data 表读取已验证样本，训练一个轻量级 DecisionTreeClassifier，
保存为 <config_dir>/smart_agent_model.pkl，供 FastBrainEngine 实时加载推理。

设计目标：
  - 每家用户独立训练，模型完全个性化，不与任何其他用户共享数据
  - 推理耗时 <1ms（Decision Tree 远快于 LLM）；内存缓存避免每次读磁盘
  - 冷启动友好：样本不足时自动跳过训练，退化到 behavior_patterns 匹配
  - 可解释：模型规则可转储为文本，方便调试和用户查看

三阶段进化：
  阶段 0 (< 50 条样本)  → 退化到现有 behavior_patterns 启发式匹配
  阶段 1 (50~200 条)    → DecisionTree(max_depth=4)，防过拟合
  阶段 2 (> 200 条)     → DecisionTree(max_depth=8)，完全个性化

P3 联邦学习预留接口：
  upload_gradient() / download_prior() — 当前为空实现，
  未来接入云端聚合服务时补全，不上传原始数据（仅上传模型梯度）。
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Callable

_LOGGER = logging.getLogger(__name__)

# 默认路径（标准 HA 部署 Linux /config/）；优先使用 hass.config.config_dir 动态拼接
MODEL_FILENAME = "smart_agent_model.pkl"
MODEL_PATH = f"/config/{MODEL_FILENAME}"          # 兜底默认值

MIN_SAMPLES_STAGE1 = 50    # 进入阶段 1 的最低样本数
MIN_SAMPLES_STAGE2 = 200   # 进入阶段 2 的样本数
MIN_PROBA_THRESHOLD = 0.70 # 模型预测置信度低于此值则退回启发式

# 特征键顺序（与 to_vector 严格对应，升级时同步更新此列表）
FEATURE_KEYS = [
    "time_hour",         # 0-23 整数
    "is_weekend",        # 0/1
    "trigger_domain",    # binary_sensor=0, sensor=1, other=2
    "room_person_count", # 0,1,2,...
    "outdoor_temp",      # 连续浮点，缺失值填 20.0
    "season_encoding",   # spring=0, summer=1, autumn=2, winter=3
]

_SEASON_MAP = {"spring": 0, "summer": 1, "autumn": 2, "winter": 3}
_DOMAIN_MAP = {"binary_sensor": 0, "sensor": 1}

# ── 模块级内存缓存（H3：避免每次推理都读磁盘）────────────────────────────────
# 结构：{"path": str, "mtime": float, "pkg": dict | None}
_MODEL_CACHE: dict = {"path": "", "mtime": 0.0, "pkg": None}


def resolve_model_path(config_dir: str | None = None) -> str:
    """
    根据 config_dir 计算模型文件路径。

    Args:
        config_dir: hass.config.config_dir，为 None 时返回默认兜底路径。
    """
    if config_dir:
        return os.path.join(config_dir, MODEL_FILENAME)
    return MODEL_PATH


class LocalModelTrainer:
    """
    从 SQLite training_data 表读取样本，训练并持久化本地决策树模型。

    Args:
        db_query_func: 接受 SQL 字符串并返回 list[dict] 的函数（注入自 PatrolMixin._query_events）
        model_path:    模型保存路径；传入 hass.config.config_dir 拼接的绝对路径，
                       默认使用 MODEL_PATH 兜底值。
    """

    def __init__(self, db_query_func: Callable | None, model_path: str = MODEL_PATH):
        self._query = db_query_func
        self._model_path = model_path

    # ── 训练入口 ──────────────────────────────────────────────────────────────

    def train(self) -> bool:
        """
        从数据库读取已验证样本，训练决策树并保存模型。

        Returns:
            True 表示训练成功并保存模型；False 表示样本不足或训练失败。
        """
        if self._query is None:
            _LOGGER.warning("[ModelTrainer] db_query_func 未注入，跳过训练")
            return False

        rows = self._query(
            "SELECT feature_json, decision_json, label FROM training_data "
            "WHERE is_verified=1 AND label IS NOT NULL AND feature_json IS NOT NULL"
        )

        if not rows or len(rows) < MIN_SAMPLES_STAGE1:
            _LOGGER.info(
                "[ModelTrainer] 已验证样本 %d 条，不足 %d 条，跳过训练",
                len(rows) if rows else 0,
                MIN_SAMPLES_STAGE1,
            )
            return False

        X, y = [], []
        skipped = 0
        for r in rows:
            try:
                feat = json.loads(r["feature_json"])
                dec = json.loads(r["decision_json"])
                actions = dec.get("actions", [])
                if not actions:
                    skipped += 1
                    continue
                # 取置信度最高的动作作为标签
                best_action = max(actions, key=lambda a: a.get("confidence", 0) if isinstance(a, dict) else 0)
                eid = best_action.get("entity_id", "")
                svc = best_action.get("service", "")
                if not eid or not svc:
                    skipped += 1
                    continue
                _domain = eid.split(".", 1)[0] if "." in eid else ""
                if _domain not in {"light", "switch", "climate", "fan", "cover", "media_player"}:
                    skipped += 1
                    continue
                label = f"{eid}:{svc}"
                # 负样本（用户修正）参与训练但标为 "nothing:{eid}"
                if r.get("label") == 0:
                    label = f"nothing:{eid}"
                vec = self.to_vector(feat)
                X.append(vec)
                y.append(label)
            except Exception as exc:
                _LOGGER.debug("[ModelTrainer] 跳过损坏样本: %s", exc)
                skipped += 1
                continue

        total = len(X)
        _LOGGER.info("[ModelTrainer] 有效样本 %d 条，跳过 %d 条", total, skipped)

        if total < MIN_SAMPLES_STAGE1:
            _LOGGER.info("[ModelTrainer] 有效样本不足，跳过训练")
            return False

        # 根据样本量选择树深度
        max_depth = 4 if total < MIN_SAMPLES_STAGE2 else 8
        stage = 1 if total < MIN_SAMPLES_STAGE2 else 2

        try:
            from sklearn.tree import DecisionTreeClassifier
            import joblib

            clf = DecisionTreeClassifier(
                max_depth=max_depth,
                min_samples_leaf=3,
                class_weight="balanced",  # 平衡少数类
            )
            clf.fit(X, y)

            pkg = {
                "model": clf,
                "samples": total,
                "stage": stage,
                "trained_at": datetime.now().isoformat(),
                "feature_keys": FEATURE_KEYS,
            }

            # L3: 原子写入（先写 .tmp 再 os.replace，防止读写竞态破坏文件）
            tmp_path = self._model_path + ".tmp"
            joblib.dump(pkg, tmp_path)
            os.replace(tmp_path, self._model_path)

            # L2: 保存轻量元数据 sidecar（model_info() 只读此文件，不加载整个模型）
            meta = {
                "samples": total,
                "stage": stage,
                "trained_at": pkg["trained_at"],
                "feature_keys": FEATURE_KEYS,
            }
            meta_path = self._model_path.replace(".pkl", "_meta.json")
            with open(meta_path, "w", encoding="utf-8") as _mf:
                json.dump(meta, _mf, ensure_ascii=False)

            # ── 关键：训练完成后立即预热 _MODEL_CACHE（此处在 executor 线程，安全执行磁盘 I/O）──
            # 目的：确保 predict() 在 HA 事件循环（@callback）中始终命中内存缓存，
            # 不触发 joblib.load() 阻塞 I/O，避免 HA 2025.x 阻塞调用检测警告。
            global _MODEL_CACHE
            _MODEL_CACHE = {
                "path": self._model_path,
                "mtime": os.path.getmtime(self._model_path),
                "pkg": pkg,
            }

            _LOGGER.info(
                "[ModelTrainer] 阶段 %d 模型训练完成 | 样本: %d | 深度: %d | 标签数: %d | 保存至: %s",
                stage, total, max_depth, len(set(y)), self._model_path,
            )
            return True
        except ImportError:
            # scikit-learn 是可选依赖，HA 容器中 Python 3.14 暂无预编译 wheel，
            # 不在 requirements 中强制安装，系统降级到启发式匹配，功能正常。
            # 若需启用本地 ML 训练，可通过 SSH/Terminal 手动 pip install scikit-learn joblib
            _LOGGER.info(
                "[ModelTrainer] scikit-learn 未安装，本地 ML 训练跳过（FastBrain 使用启发式匹配，功能正常）"
            )
            return False
        except Exception as exc:
            _LOGGER.error("[ModelTrainer] 训练失败: %s", exc)
            return False

    # ── 推理接口 ─────────────────────────────────────────────────────────────

    @staticmethod
    def predict(features: dict, model_path: str = MODEL_PATH) -> tuple[str | None, float]:
        """
        用已保存的本地模型预测最优动作（内存缓存版本，避免每次读磁盘）。

        Args:
            features:   FeatureEncoder.encode() 输出的特征字典
            model_path: 模型文件路径（由调用方传入 config_dir 拼接路径）

        Returns:
            (label, probability) — label 格式为 "entity_id:service"；
            若模型不存在、版本不匹配或置信度不足则返回 (None, 0.0)
        """
        global _MODEL_CACHE
        if not os.path.exists(model_path):
            return None, 0.0
        try:
            import joblib
            # H3: mtime 检测，仅在文件更新时才重新加载
            # HA 2025.x 兼容性：predict() 可能在 @callback（事件循环）中被调用。
            # 若缓存已热（mtime 未变）→ 纯 CPU 推理，无 I/O，安全。
            # 若缓存过冷（mtime 变了）→ 跳过本次推理（返回 None），
            #   train() 在 executor 中完成后会立即预热缓存，下次调用命中缓存。
            mtime = os.path.getmtime(model_path)
            if _MODEL_CACHE["path"] != model_path or _MODEL_CACHE["mtime"] != mtime:
                # 缓存冷：判断是否在事件循环中（HA @callback 环境）
                try:
                    import asyncio as _asyncio
                    _asyncio.get_running_loop()
                    # 有事件循环 → 在 @callback 中，跳过阻塞加载，等待 train() 预热
                    _LOGGER.debug(
                        "[ModelTrainer] 模型缓存过期但在事件循环中，跳过加载（等待 train() 预热缓存）"
                    )
                    return None, 0.0
                except RuntimeError:
                    # 没有事件循环 → 在 executor/线程中，安全执行磁盘加载
                    pkg = joblib.load(model_path)
                    _MODEL_CACHE = {"path": model_path, "mtime": mtime, "pkg": pkg}
                    _LOGGER.info("[ModelTrainer] 模型已从磁盘重新加载（executor 线程，path=%s）", model_path)
            pkg = _MODEL_CACHE["pkg"]
            if pkg is None:
                return None, 0.0

            # M2: 特征键版本校验，防止代码升级后旧模型输入维度错位
            if pkg.get("feature_keys") != FEATURE_KEYS:
                _LOGGER.warning(
                    "[ModelTrainer] 模型 feature_keys 与当前版本不匹配（旧模型需重训练），跳过预测"
                )
                return None, 0.0

            clf = pkg["model"]
            vec = [LocalModelTrainer.to_vector(features)]
            proba_arr = clf.predict_proba(vec)[0]
            max_proba = float(proba_arr.max())
            if max_proba < MIN_PROBA_THRESHOLD:
                return None, max_proba
            label = clf.classes_[proba_arr.argmax()]
            return label, max_proba
        except Exception as exc:
            _LOGGER.warning("[ModelTrainer] 推理失败: %s", exc)
            return None, 0.0

    @staticmethod
    def model_info(model_path: str = MODEL_PATH) -> dict:
        """
        返回当前模型元数据（用于面板展示）。

        L2 优化：优先读轻量 sidecar JSON，避免为获取元数据而加载整个 pkl。
        """
        meta_path = model_path.replace(".pkl", "_meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, encoding="utf-8") as _mf:
                    data = json.load(_mf)
                data["status"] = "ok"
                return data
            except Exception:
                pass
        # 兜底：无 sidecar 时加载完整模型（向后兼容旧版本）
        if not os.path.exists(model_path):
            return {"status": "no_model"}
        try:
            import joblib
            pkg = joblib.load(model_path)
            return {
                "status": "ok",
                "samples": pkg.get("samples", 0),
                "stage": pkg.get("stage", 0),
                "trained_at": pkg.get("trained_at", ""),
            }
        except Exception:
            return {"status": "error"}

    # ── 特征向量转换 ──────────────────────────────────────────────────────────

    @staticmethod
    def to_vector(feat: dict) -> list[float]:
        """
        将 FeatureEncoder 输出的特征字典转换为固定长度数值向量。

        向量顺序严格对应 FEATURE_KEYS，训练和推理必须使用同一方法。
        注意：outdoor_temp 用 `is None` 检测缺失，防止 0.0（零度）被 or 误判为缺失值。
        """
        _temp = feat.get("outdoor_temp")
        return [
            float(feat.get("time_hour", 12)),
            1.0 if feat.get("is_weekend") else 0.0,
            float(_DOMAIN_MAP.get(feat.get("trigger_domain", ""), 2)),
            float(feat.get("room_person_count") or 0),
            float(_temp if _temp is not None else 20.0),   # L1: 0°C 不被 or 误替换
            float(_SEASON_MAP.get(feat.get("season_encoding", "summer"), 1)),
        ]

    # ── P3 联邦学习预留接口（当前为空实现）────────────────────────────────────

    def upload_gradient(self, server_url: str) -> bool:
        """
        [P3 预留] 上传本地模型梯度到联邦学习服务器。

        注意：只上传梯度，不上传原始训练数据，保护用户隐私。
        当前为空实现，联邦学习服务端就绪后补全。
        """
        _LOGGER.debug("[ModelTrainer] upload_gradient: P3 联邦学习尚未启用")
        return False

    def download_prior(self, server_url: str) -> bool:
        """
        [P3 预留] 从联邦服务器下载聚合先验模型（用于新用户冷启动）。

        当前为空实现，联邦学习服务端就绪后补全。
        """
        _LOGGER.debug("[ModelTrainer] download_prior: P3 联邦学习尚未启用")
        return False
