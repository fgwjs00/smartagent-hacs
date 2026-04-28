/**
 * SmartAgent Panel — esbuild 构建脚本
 *
 * 用法:
 *   node build.mjs          — 开发构建（可读格式），输出到 dist/smart-agent-panel.js
 *   node build.mjs --prod   — 生产构建，输出覆盖 smart-agent-panel.js（部署时使用）
 *   node build.mjs --minify — 额外生成压缩版 smart-agent-panel.min.js
 *   node build.mjs --watch  — 监听模式（文件变更自动重建到 dist/）
 *
 * ── 文件保护 ──
 * 默认输出到 dist/ 子目录，不覆盖工作目录中的 smart-agent-panel.js。
 * 使用 --prod 标志才会将构建结果写入生产文件。
 */

import * as esbuild from "./node_modules/esbuild/lib/main.js";
import { statSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dir = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const minify = args.includes("--minify");
const watch  = args.includes("--watch");
const prod   = args.includes("--prod");   // 覆盖生产文件

// dist/ 用于开发/CI 输出，避免意外覆盖已部署的生产文件
const distDir = resolve(__dir, "dist");
mkdirSync(distDir, { recursive: true });

const outDev  = prod ? resolve(__dir, "smart-agent-panel.js") : resolve(distDir, "smart-agent-panel.js");
const outMin  = prod ? resolve(__dir, "smart-agent-panel.min.js") : resolve(distDir, "smart-agent-panel.min.js");
const outfile = outDev;

/** 构建完成后报告文件大小 */
function reportSize(file) {
  try {
    const bytes = statSync(file).size;
    const kb = (bytes / 1024).toFixed(1);
    console.log(`  ✓ ${file.replace(__dir, ".")}  ${kb} KB`);
  } catch {}
}

const buildOptions = {
  entryPoints: [resolve(__dir, "src/index.js")],
  bundle: true,
  format: "iife",
  globalName: "_SmartAgentPanel",   // 保持 IIFE，不污染全局
  target: ["es2020", "chrome90"],
  charset: "utf8",
  legalComments: "none",
};

if (watch) {
  // ── 监听模式 ──
  const ctx = await esbuild.context({
    ...buildOptions,
    outfile,
    minify: false,
    sourcemap: "inline",
    plugins: [{
      name: "report",
      setup(build) {
        build.onEnd(result => {
          if (result.errors.length > 0) {
            console.error("[build] ✗ 构建失败");
          } else {
            console.log(`[build] ✓ ${new Date().toLocaleTimeString()} — 重建完成`);
            reportSize(outfile);
          }
        });
      },
    }],
  });
  await ctx.watch();
  console.log("[watch] 监听 src/ 目录变更，Ctrl+C 停止...");
} else {
  // ── 单次构建 ──
  console.log(`[build] 开始构建 (${minify ? "压缩模式" : "开发模式"})...`);

  // 开发版（可读）
  await esbuild.build({
    ...buildOptions,
    outfile,
    minify: false,
    sourcemap: false,
  });
  reportSize(outfile);

  // 压缩版（可选）
  if (minify) {
    await esbuild.build({
      ...buildOptions,
      outfile: outMin,
      minify: true,
      sourcemap: false,
    });
    reportSize(outMin);
  }

  console.log("[build] 完成 ✓");
}
