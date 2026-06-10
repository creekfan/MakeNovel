"use client";

import { useSettingsStore } from '@/store';

export default function SettingsPage() {
  const store = useSettingsStore();

  return (
    <div className="max-w-xl mx-auto p-8">
      <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 mb-6">全局设置</h1>

      <div className="space-y-6">
        {/* Provider */}
        <div className="bg-white dark:bg-zinc-800 p-5 rounded-xl border border-zinc-200 dark:border-zinc-700">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-3">默认 LLM 提供商</h3>
          <select
            value={store.provider}
            onChange={(e) => store.setProvider(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="deepseek">DeepSeek</option>
            <option value="ollama">Ollama (本地)</option>
          </select>
        </div>

        {/* OpenAI */}
        {store.provider === 'openai' && (
          <div className="bg-white dark:bg-zinc-800 p-5 rounded-xl border border-zinc-200 dark:border-zinc-700 space-y-3">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">OpenAI 配置</h3>
            <input
              type="password"
              value={store.openaiKey}
              onChange={(e) => store.setOpenaiKey(e.target.value)}
              placeholder="API Key"
              className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            />
            <input
              value={store.openaiModel}
              onChange={(e) => store.setOpenaiModel(e.target.value)}
              placeholder="模型名称 (默认: gpt-4o)"
              className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            />
          </div>
        )}

        {/* Anthropic */}
        {store.provider === 'anthropic' && (
          <div className="bg-white dark:bg-zinc-800 p-5 rounded-xl border border-zinc-200 dark:border-zinc-700 space-y-3">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Anthropic 配置</h3>
            <input
              type="password"
              value={store.anthropicKey}
              onChange={(e) => store.setAnthropicKey(e.target.value)}
              placeholder="API Key"
              className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            />
            <input
              value={store.anthropicModel}
              onChange={(e) => store.setAnthropicModel(e.target.value)}
              placeholder="模型名称 (默认: claude-3-5-sonnet)"
              className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            />
          </div>
        )}

        {/* DeepSeek */}
        {store.provider === 'deepseek' && (
          <div className="bg-white dark:bg-zinc-800 p-5 rounded-xl border border-zinc-200 dark:border-zinc-700 space-y-3">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">DeepSeek 配置</h3>
            <input
              type="password"
              value={store.deepseekKey}
              onChange={(e) => store.setDeepseekKey(e.target.value)}
              placeholder="API Key"
              className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            />
            <input
              value={store.deepseekModel}
              onChange={(e) => store.setDeepseekModel(e.target.value)}
              placeholder="模型名称 (默认: deepseek-chat)"
              className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            />
          </div>
        )}

        {/* Ollama */}
        {store.provider === 'ollama' && (
          <div className="bg-white dark:bg-zinc-800 p-5 rounded-xl border border-zinc-200 dark:border-zinc-700 space-y-3">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Ollama 配置</h3>
            <input
              value={store.ollamaUrl}
              onChange={(e) => store.setOllamaUrl(e.target.value)}
              placeholder="Base URL (默认: http://localhost:11434)"
              className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            />
            <input
              value={store.ollamaModel}
              onChange={(e) => store.setOllamaModel(e.target.value)}
              placeholder="模型名称 (默认: llama3)"
              className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            />
          </div>
        )}

        {/* 创作准备专用提供商（独立于主写作模型） */}
        <div className="bg-white dark:bg-zinc-800 p-5 rounded-xl border border-zinc-200 dark:border-zinc-700 space-y-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">创作准备专用模型</h3>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">分担 token 压力</span>
          </div>
          <p className="text-xs text-zinc-500">用于创作准备阶段的角色/设定推荐，独立于主写作模型。</p>
          <select
            value={store.recommendProvider}
            onChange={(e) => store.setRecommendProvider(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
          >
            <option value="gemini">Google Gemini（免费）</option>
            <option value="deepseek">DeepSeek</option>
          </select>

          {store.recommendProvider === 'gemini' && (
            <div className="space-y-3 pt-2 border-t border-zinc-100 dark:border-zinc-700">
              <input
                type="password"
                value={store.geminiKey}
                onChange={(e) => store.setGeminiKey(e.target.value)}
                placeholder="API Key (Google AI Studio)"
                className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
              />
              <input
                value={store.recommendModel || store.geminiModel}
                onChange={(e) => store.setRecommendModel(e.target.value)}
                placeholder="推荐模型 (默认: gemini-2.5-flash)"
                className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
              />
            </div>
          )}

          {store.recommendProvider === 'deepseek' && (
            <div className="space-y-3 pt-2 border-t border-zinc-100 dark:border-zinc-700">
              <input
                type="password"
                value={store.deepseekKey}
                onChange={(e) => store.setDeepseekKey(e.target.value)}
                placeholder="API Key"
                className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
              />
              <input
                value={store.recommendModel || 'deepseek-chat'}
                onChange={(e) => store.setRecommendModel(e.target.value)}
                placeholder="推荐模型 (默认: deepseek-chat)"
                className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
              />
            </div>
          )}
        </div>

        <div className="text-xs text-zinc-400">
          注：设置保存在浏览器本地，不会上传到服务器。API Key 会在后端 `.env` 文件中配置。
        </div>
      </div>
    </div>
  );
}
