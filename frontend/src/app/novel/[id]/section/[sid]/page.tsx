"use client";

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft, Wand2, Save, Loader2, ChevronRight, ChevronDown } from 'lucide-react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { api } from '@/lib/api';
import { useSettingsStore } from '@/store';
import type { AIAction, OutlineNode, Character, Setting } from '@/types';

export default function SectionEditorPage() {
  const params = useParams();
  const router = useRouter();
  const novelId = Number(params.id);
  const sectionId = Number(params.sid);
  const settingsStore = useSettingsStore();

  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const [section, setSection] = useState<OutlineNode | null>(null);
  const [hierarchy, setHierarchy] = useState<{ title: string; id: number }[]>([]);
  const [prevSummary, setPrevSummary] = useState('');
  const [characters, setCharacters] = useState<Character[]>([]);
  const [worldSettings, setWorldSettings] = useState<Setting[]>([]);
  const [contextExpanded, setContextExpanded] = useState(true);
  const [showContextPicker, setShowContextPicker] = useState(false);
  const [activeCharIds, setActiveCharIds] = useState<number[]>([]);
  const [activeSettingIds, setActiveSettingIds] = useState<number[]>([]);
  const searchParams = useSearchParams();

  const editor = useEditor({
    extensions: [StarterKit.configure({ heading: { levels: [1, 2, 3] } }), Placeholder.configure({ placeholder: '开始写作...' })],
    content: '', editorProps: { attributes: { class: 'tiptap prose prose-zinc dark:prose-invert max-w-none focus:outline-none min-h-[400px] px-4 py-3' } },
    onUpdate: ({ editor: ed }) => { setWordCount(ed.getText().length); },
  });

  const [aiOpen, setAiOpen] = useState(false);
  const [aiActions, setAiActions] = useState<AIAction[]>([]);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiOutput, setAiOutput] = useState('');
  const [aiInstruction, setAiInstruction] = useState('');
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmAction, setConfirmAction] = useState<AIAction | null>(null);
  const [confirmText, setConfirmText] = useState('');
  const savedSelectionRef = useRef<{ from: number; to: number } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const allChars = await api.listCharacters(novelId);
        setCharacters(allChars);
        const allSettings = await api.listSettings(novelId);
        setWorldSettings(allSettings);
        const charParam = searchParams.get('chars');
        const settingParam = searchParams.get('settings');
        setActiveCharIds(charParam ? charParam.split(',').map(Number) : allChars.map(c => c.id));
        setActiveSettingIds(settingParam ? settingParam.split(',').map(Number) : allSettings.map(s => s.id));

        const outlines = await api.listOutline(novelId);

        const findNodeWithPath = (nodes: OutlineNode[], path: { title: string; id: number }[]): OutlineNode | null => {
          for (const n of nodes) {
            if (n.id === sectionId) return n;
            if (n.children && n.children.length > 0) {
              const found = findNodeWithPath(n.children, [...path, { title: n.title, id: n.id }]);
              if (found) return found;
            }
          }
          return null;
        };

        const buildPath = (nodes: OutlineNode[], targetId: number, path: { title: string; id: number }[] = []): { title: string; id: number }[] | null => {
          for (const n of nodes) {
            if (n.id === targetId) return [...path, { title: n.title, id: n.id }];
            if (n.children && n.children.length > 0) {
              const result = buildPath(n.children, targetId, [...path, { title: n.title, id: n.id }]);
              if (result) return result;
            }
          }
          return null;
        };

        const sec = findNodeWithPath(outlines, []);
        const path = buildPath(outlines, sectionId);
        if (path) setHierarchy(path);
        if (!sec) { router.push(`/novel/${novelId}/outline`); return; }

        setSection(sec);
        setTitle(sec.title);
        if (editor) editor.commands.setContent(sec.content || '');

        // Find previous section's summary for write context
        const collectScenes = (nodes: OutlineNode[]): OutlineNode[] => {
          const result: OutlineNode[] = [];
          for (const n of nodes) {
            if (n.node_type === 'scene') result.push(n);
            if (n.children) result.push(...collectScenes(n.children));
          }
          return result;
        };
        const allScenes = collectScenes(outlines);
        const idx = allScenes.findIndex(s => s.id === sectionId);
        if (idx > 0 && allScenes[idx - 1].notes) {
          setPrevSummary(allScenes[idx - 1].notes);
        }
        setLoading(false);
      } catch { router.push(`/novel/${novelId}`); }
    })();
  }, [sectionId, novelId, router, editor]);

  useEffect(() => { api.listActions().then(setAiActions); }, []);

  const handleSave = useCallback(async () => {
    if (!editor) return;
    setSaving(true);
    try { await api.updateOutlineNode(sectionId, { title, content: editor.getHTML() }); } catch {}
    setSaving(false);
  }, [editor, sectionId, title]);

  useEffect(() => { const h = (e: KeyboardEvent) => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); handleSave(); } }; window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h); }, [handleSave]);
  useEffect(() => { const i = setInterval(() => { if (editor && editor.getText().length > 0) handleSave(); }, 30000); return () => clearInterval(i); }, [handleSave, editor]);

  const getCreds = () => ({
    provider: settingsStore.provider,
    model: settingsStore.provider === "openai" ? settingsStore.openaiModel : settingsStore.provider === "anthropic" ? settingsStore.anthropicModel : settingsStore.provider === "deepseek" ? settingsStore.deepseekModel : settingsStore.provider === "ollama" ? settingsStore.ollamaModel : "",
    apiKey: settingsStore.provider === "openai" ? settingsStore.openaiKey : settingsStore.provider === "anthropic" ? settingsStore.anthropicKey : settingsStore.provider === "deepseek" ? settingsStore.deepseekKey : settingsStore.provider === "ollama" ? settingsStore.ollamaUrl : "",
  });

  const handleAIAction = (action: AIAction) => {
    if (!editor) return;
    const { from, to } = editor.state.selection;
    savedSelectionRef.current = { from, to };
    setConfirmText(editor.state.doc.textBetween(from, to));
    setConfirmAction(action);
    setShowConfirm(true);
  };

  const handleConfirmAI = async () => {
    if (!confirmAction || !editor) return;
    const action = confirmAction;
    setShowConfirm(false); setActiveAction(action.action); setAiGenerating(true); setAiOutput('');
    const sel = savedSelectionRef.current;
    let selectedText = '';
    if (action.action === 'write') { selectedText = editor.getText(); }
    else if (action.action === 'polish' && sel) { selectedText = editor.state.doc.textBetween(sel.from, sel.to); }
    else if (action.action === 'rewrite' && sel) {
      const selText = editor.state.doc.textBetween(sel.from, sel.to);
      const beforeCtx = editor.state.doc.textBetween(Math.max(0, sel.from - 500), sel.from);
      const afterCtx = editor.state.doc.textBetween(sel.to, Math.min(editor.state.doc.content.size, sel.to + 500));
      selectedText = `【待改写内容】\n${selText}\n\n【上文】${beforeCtx || '（无）'}\n\n【下文】${afterCtx || '（无）'}`;
    }
    else if (action.action === 'brainstorm') { selectedText = editor.getText(); }
    else if (action.action === 'summary') { selectedText = editor.getText(); }
    const creds = getCreds();
    const writeInstruction = action.action === 'write' && section
      ? `【${section.title}】${section.summary || ''}${prevSummary ? '\n\n## 上一节摘要\n' + prevSummary : ''}${aiInstruction ? '\n\n补充要求：' + aiInstruction : ''}`
      : aiInstruction;
    try {
      const response = await api.generateAI({ novel_id: novelId, action: action.action, selected_text: selectedText, instruction: writeInstruction, provider: creds.provider, model: creds.model, api_key: creds.apiKey, active_character_ids: activeCharIds, active_setting_ids: activeSettingIds });
      const reader = response.body?.getReader(); const decoder = new TextDecoder();
      if (!reader) return;
      while (true) { const { done, value } = await reader.read(); if (done) break; for (const line of decoder.decode(value, { stream: true }).split('\n')) { if (line.startsWith('data: ')) { const data = line.slice(6).trim(); if (data === '[DONE]') break; try { setAiOutput((p) => p + (JSON.parse(data).token || '')); } catch {} } } }
    } catch (e) { setAiOutput(`[AI 调用出错: ${(e as Error).message}]`); }
    setAiGenerating(false);
  };

  const handleInsertAIText = () => {
    if (!editor || !aiOutput) return;
    const sel = savedSelectionRef.current;
    if ((activeAction === 'polish' || activeAction === 'rewrite') && sel && sel.from !== sel.to) { editor.chain().focus().setTextSelection({ from: sel.from, to: sel.to }).deleteSelection().insertContent(aiOutput).run(); }
    else if (sel) { editor.chain().focus().setTextSelection(sel.from).insertContent(aiOutput).run(); }
    else { editor.chain().focus().insertContent(aiOutput).run(); }
    setAiOutput(''); setActiveAction(null); setAiInstruction(''); savedSelectionRef.current = null;
  };

  const handleSaveSummary = async () => {
    if (!aiOutput) return;
    await api.updateOutlineNode(sectionId, { notes: aiOutput.trim() });
    setAiOutput(''); setActiveAction(null); setAiInstruction('');
    // Reload section data
    const outlines = await api.listOutline(novelId);
    const findNode = (nodes: OutlineNode[]): OutlineNode | null => {
      for (const n of nodes) { if (n.id === sectionId) return n; if (n.children) { const f = findNode(n.children); if (f) return f; } }
      return null;
    };
    const s = findNode(outlines);
    if (s) setSection(s);
  };

  const checkDisabled = (a: AIAction) => aiGenerating || (a.requires_text && editor?.state.selection.empty);

  if (loading) return <div className="p-8 text-zinc-500">加载中...</div>;

  return (
    <div className="flex h-[calc(100vh-0px)]">
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center gap-3 px-6 py-2.5 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
          <button onClick={() => router.push(`/novel/${novelId}`)} className="p-1 text-zinc-400 hover:text-zinc-600 cursor-pointer"><ArrowLeft size={18} /></button>
          <div className="flex items-center gap-1 text-xs text-zinc-400 overflow-x-auto">
            {hierarchy.map((h, i) => (
              <span key={h.id} className="flex items-center gap-1">
                <button onClick={() => router.push(`/novel/${novelId}/outline#${h.id}`)} className="hover:text-indigo-500 cursor-pointer truncate max-w-[100px]">{h.title}</button>
                {i < hierarchy.length - 1 && <ChevronRight size={10} className="shrink-0" />}
              </span>
            ))}
          </div>
          <input value={title} onChange={(e) => setTitle(e.target.value)} className="text-base font-semibold bg-transparent text-zinc-900 dark:text-zinc-100 outline-none min-w-0" placeholder="节标题" />
          <span className="text-xs text-zinc-400 font-mono ml-auto shrink-0">{wordCount.toLocaleString()} 字</span>
          <button onClick={handleSave} disabled={saving} className="flex items-center gap-1 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 cursor-pointer shrink-0"><Save size={14} />{saving ? '...' : '保存'}</button>
          <button onClick={() => setAiOpen(!aiOpen)} className={`flex items-center gap-1 px-2.5 py-1.5 text-sm rounded-lg cursor-pointer shrink-0 ${aiOpen ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400' : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'}`}><Wand2 size={14} />AI</button>
        </div>

        {section && (
          <div className="px-6 py-1.5 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50">
            <button onClick={() => setContextExpanded(!contextExpanded)} className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-700 cursor-pointer">
              {contextExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              创作上下文
            </button>
            <button onClick={() => setShowContextPicker(!showContextPicker)}
              className="ml-3 text-xs px-2 py-0.5 rounded border border-zinc-200 dark:border-zinc-600 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer">
              选择注入：角色{activeCharIds.length}/{characters.length} 设定{activeSettingIds.length}/{worldSettings.length}
            </button>
            {contextExpanded && (
              <div className="flex gap-4 text-xs text-zinc-500 mt-1 pb-1 flex-wrap">
                {section.summary && <span>情节：{section.summary.slice(0, 60)}{section.summary.length > 60 ? '…' : ''}</span>}
                {section.notes && <span className="text-indigo-500">摘要：{section.notes.slice(0, 80)}{section.notes.length > 80 ? '…' : ''}</span>}
                {characters.length > 0 && <span>角色：{characters.slice(0, 3).map(c => c.name).join('、')}</span>}
                {prevSummary && <span className="text-amber-500">← 上节：{prevSummary.slice(0, 60)}{prevSummary.length > 60 ? '…' : ''}</span>}
              </div>
            )}
          </div>
        )}

        {showContextPicker && (
          <div className="px-6 py-3 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/30 max-h-64 overflow-y-auto">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-zinc-600">注入角色 ({activeCharIds.length}/{characters.length})</span>
                  <span className="flex gap-1">
                    <button onClick={() => setActiveCharIds(characters.map(c => c.id))} className="text-[10px] text-indigo-500 hover:underline cursor-pointer">全选</button>
                    <button onClick={() => setActiveCharIds([])} className="text-[10px] text-zinc-400 hover:underline cursor-pointer">清除</button>
                  </span>
                </div>
                {characters.map(c => (
                  <label key={c.id} className="flex items-center gap-1.5 py-0.5 text-xs text-zinc-700 dark:text-zinc-300 cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800 rounded px-1">
                    <input type="checkbox" checked={activeCharIds.includes(c.id)} onChange={() => setActiveCharIds(p => p.includes(c.id) ? p.filter(id => id !== c.id) : [...p, c.id])}
                      className="rounded" />
                    {c.name}
                  </label>
                ))}
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-zinc-600">注入设定 ({activeSettingIds.length}/{worldSettings.length})</span>
                  <span className="flex gap-1">
                    <button onClick={() => setActiveSettingIds(worldSettings.map(s => s.id))} className="text-[10px] text-indigo-500 hover:underline cursor-pointer">全选</button>
                    <button onClick={() => setActiveSettingIds([])} className="text-[10px] text-zinc-400 hover:underline cursor-pointer">清除</button>
                  </span>
                </div>
                {worldSettings.map(s => (
                  <label key={s.id} className="flex items-center gap-1.5 py-0.5 text-xs text-zinc-700 dark:text-zinc-300 cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800 rounded px-1">
                    <input type="checkbox" checked={activeSettingIds.includes(s.id)} onChange={() => setActiveSettingIds(p => p.includes(s.id) ? p.filter(id => id !== s.id) : [...p, s.id])}
                      className="rounded" />
                    {s.name}
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-auto bg-white dark:bg-zinc-950"><div className="max-w-3xl mx-auto py-6"><EditorContent editor={editor} /></div></div>
      </div>

      {aiOpen && (
        <div className="w-80 border-l border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 flex flex-col shrink-0 overflow-hidden">
          <div className="p-3 border-b"><h3 className="font-semibold text-sm text-zinc-900 dark:text-zinc-100">AI 写作助手</h3><p className="text-xs text-zinc-500 mt-0.5">{showConfirm ? '确认发送' : '大纲上下文已自动注入'}</p></div>

          {showConfirm && confirmAction ? (
            <div className="flex-1 overflow-auto p-3 space-y-3">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-medium">{confirmAction.label}</span>
                  {confirmAction.action === 'write' && <span className="text-[10px] text-sky-600 bg-sky-50 dark:bg-sky-900/20 px-1.5 py-0.5 rounded">大纲驱动创作</span>}
                  {confirmAction.action === 'polish' && <span className="text-[10px] text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-1.5 py-0.5 rounded">替换选中</span>}
                  {confirmAction.action === 'rewrite' && <span className="text-[10px] text-rose-600 bg-rose-50 dark:bg-rose-900/20 px-1.5 py-0.5 rounded">替换选中(1000字)</span>}
                </div>

                {confirmAction.action === 'write' && section && (
                  <div className="mb-3">
                    <label className="text-xs text-zinc-400 block mb-1">本节大纲</label>
                    <div className="text-sm text-zinc-700 dark:text-zinc-300 bg-zinc-50 dark:bg-zinc-800 rounded-lg p-2 max-h-24 overflow-auto whitespace-pre-wrap">
                      【{section.title}】{section.summary || '（无情节概要）'}
                    </div>
                    {prevSummary && <div className="mt-2 text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-2">← 上一节摘要：{prevSummary.slice(0, 200)}{prevSummary.length > 200 ? '…' : ''}</div>}
                    <p className="text-[10px] text-zinc-400 mt-1">大纲、角色档案、世界观设定将自动注入 system prompt</p>
                  </div>
                )}
                {confirmAction.action === 'polish' && <div className="mb-2"><label className="text-xs text-zinc-400 block mb-1">选中原文</label><div className="text-sm text-zinc-700 dark:text-zinc-300 bg-zinc-50 dark:bg-zinc-800 rounded-lg p-2 max-h-24 overflow-auto">{confirmText?.slice(0, 300) || '（无选中）'}</div></div>}
                {confirmAction.action === 'write' && <label className="text-xs text-zinc-400 block mb-1">补充创作要求（可选）</label>}
                {confirmAction.action === 'rewrite' && <label className="text-xs text-zinc-400 block mb-1">修改方向 <span className="text-red-400">*</span></label>}
                {confirmAction.action === 'polish' && <label className="text-xs text-zinc-400 block mb-1">润色要求（可选）</label>}
                {confirmAction.action === 'brainstorm' && <label className="text-xs text-zinc-400 block mb-1">创作想法</label>}
                {confirmAction.action !== 'polish' || confirmText ? (
                  <textarea value={aiInstruction} onChange={(e) => setAiInstruction(e.target.value)} placeholder={confirmAction.action === 'rewrite' ? '告诉 AI 怎么改…' : confirmAction.action === 'brainstorm' ? '创作方向…' : '要求…'} rows={3}
                    className="w-full px-2 py-1.5 text-sm border rounded-lg bg-transparent resize-none" autoFocus />
                ) : null}
              </div>
              <div className="flex gap-2"><button onClick={() => { setShowConfirm(false); setConfirmAction(null); }} className="flex-1 px-3 py-1.5 text-sm rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer">取消</button>
                <button onClick={handleConfirmAI} disabled={confirmAction.action === 'rewrite' && !aiInstruction.trim()} className="flex-1 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 cursor-pointer"><Wand2 size={14} />确认生成</button></div>
            </div>
          ) : (
            <>
              <div className="flex-1 overflow-auto p-2 space-y-1">
                {aiActions.map(a => (<button key={a.action} onClick={() => handleAIAction(a)} disabled={checkDisabled(a)}
                  className={`w-full text-left p-2.5 rounded-lg text-sm cursor-pointer ${activeAction === a.action ? 'bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200' : 'hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-transparent'} disabled:opacity-40 disabled:cursor-not-allowed`}>
                  <div className="font-medium text-zinc-900 dark:text-zinc-100">{a.label}</div><div className="text-xs text-zinc-500 mt-0.5">{a.description}</div>
                  {a.requires_text && <span className="inline-block mt-1 text-[10px] text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-1.5 py-0.5 rounded">需要选中文字</span>}
                </button>))}
              </div>
              {activeAction && !showConfirm && <div className="p-2 border-t"><input value={aiInstruction} onChange={e => setAiInstruction(e.target.value)} placeholder="调整要求后重新生成" className="w-full px-2 py-1 text-xs border rounded-lg bg-transparent" />
                <button onClick={() => { const act = aiActions.find(a => a.action === activeAction); if (act) handleAIAction(act); }} className="w-full mt-1 px-2 py-1 text-xs bg-indigo-600 text-white rounded-lg cursor-pointer"><Wand2 size={12} />重新生成</button></div>}
              <div className="border-t max-h-48 overflow-auto">
                {aiGenerating && <div className="p-3 flex items-center gap-2 text-sm text-zinc-500"><Loader2 size={14} className="animate-spin" />AI 生成中...</div>}
                {aiOutput && <div className="p-3"><div className="text-sm text-zinc-800 dark:text-zinc-200 whitespace-pre-wrap">{aiOutput}</div>
                  {activeAction === 'summary' ? (
                    <button onClick={handleSaveSummary} className="mt-2 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer w-full">保存摘要</button>
                  ) : (
                    <button onClick={handleInsertAIText} className="mt-2 px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 cursor-pointer w-full">插入到编辑器</button>
                  )}
                </div>}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
