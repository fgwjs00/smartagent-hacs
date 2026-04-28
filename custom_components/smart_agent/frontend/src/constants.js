/**
 * SmartAgent Panel — 全局常量
 * 设备域白名单、跳过关键字、域标签等配置
 */

export const TARGET_DOMAINS = [
  "light", "switch", "binary_sensor", "sensor", "climate",
  "cover", "media_player", "device_tracker", "fan",
];

export const SKIP_KW = [
  // HA 系统内置
  "sun.sun", "sensor.sun_next_", "zigbee2mqtt_bridge", "zone.", "persistent_notification",
  "script.", "automation.", "scene.", "input_", "timer.", "counter.",
  "schedule.", "weather.", "image.", "update.", "smart_agent",
  "backup.", "sensor.backup_",
  // 电池 / 信号 / 硬件诊断
  "_battery", "_battery_level", "_battery_low", "_lqi", "_rssi",
  "_linkquality", "_tamper",
  // HA 平台内部辅助
  "number.", "button.", "select.", "text.", "camera.",
  // Frigate 噪声实体（缩略图/调试）
  "_thumbnail", "_snapshot", "_debug", "frigate_version",
  // Frigate 统计计数传感器（纯数字，无动作价值）
  // 注意：_person_occupancy / _all_occupancy 不在此处过滤——
  //       binary_sensor.{zone}_person_occupancy 是布尔占用传感器，AI 可用作触发源
  "_all_count", "_all_active_count",
  "_person_count", "_person_active_count",
  "_review_alerts", "_review_detections",
  // Frigate 录像控制（不应被 AI 托管）
  "_recordings",
  // LeMesh 遥控器 MAC 传感器（仅透传按键，非受控设备）
  "_wy0c09_remote_",
  // 其他遥控器按键上报
  "_remote_on_off", "_remote_dim",
];

export const SKIP_NAME_KW = [
  "电量", "电池", "信号", "rssi", "lqi", "tamper", "篡改", "备份", "backup",
  "遥控器", "remote key", "按键上报",
];

export const DOMAIN_LABELS = {
  light: "灯光",
  switch: "开关",
  binary_sensor: "传感器",
  sensor: "数值",
  climate: "空调",
  cover: "窗帘",
  media_player: "媒体",
  device_tracker: "位置",
  fan: "风扇",
};
