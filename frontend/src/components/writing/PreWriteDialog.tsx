"use client";

import { useEffect, useState } from 'react';
import { Search, X, Edit3, Wand2, Loader2 } from 'lucide-react';
import { useCurrentNovelStore } from '@/store';
import { api } from '@/lib/api';
import type { Character, Setting } from '@/types';

interface Props {
  novelId: number;
  sectionId: number;
  sectionTitle: string;
  sectionSummary: string;
  onClose: () => void;
  onStart: (sectionId: number, charIds: number[], settingIds: number[]) => void;
}

export default function PreWriteDialog({ novelId, sectionId, sectionTitle, sectionSummary, onClose, onStart }: Props) {
  const { characters, settings, loadCharacters, loadSettings } = useCurrentNovelStore();
  const [selectedCharIds, setSelectedCharIds] = useState<number[]>([]);
  const [selectedSettingIds, setSelectedSettingIds] = useState<number[]>([]);
  const [recommending, setRecommending] = useState(true);
  const [charSearch, setCharSearch] = useState('');
  const [settingSearch, setSettingSearch] = useState('');
  const [editingChar, setEditingChar] = useState<Character | null>(null);
  const [editingSetting, setEditingSetting] = useState<Setting | null>(null);
  const [editCharForm, setEditCharForm] = useState<Record<string, string>>({});

  useEffect(() => { loadCharacters(); loadSettings(); }, []);

  // AI recommend context
  useEffect(() => {
    if (characters.length === 0 || settings.length === 0) return;
    if (!recommending) return;

    const doRecommend = async () => {
      try {
        const charList = characters.map(c => {
          const roleLabel = c.role === 'protagonist' ? '主角' : c.role === 'antagonist' ? '反派' : c.role === 'supporting' ? '配角' : '次要';
          return `- id:${c.id} ${c.name}（${roleLabel}）`;
        }).join('\n');

        const setList = settings.map(s =>
          `- id:${s.id} ${s.name}（${s.category}）`
        ).join('\n');

        const instruction = `## 本节大纲\n【${sectionTitle}】${sectionSummary || '无概要'}\n\n## 可用角色\n${charList}\n\n## 可用世界观设定\n${setList}`;

        // Read recommend provider credentials from persisted settings
        let provider = 'gemini', model = 'gemini-2.5-flash', apiKey = '';
        try {
          const raw = localStorage.getItem('makenovel-settings');
          const data = raw ? JSON.parse(raw) : {};
          const state = data.state || data;
          provider = state.recommendProvider || 'gemini';
          const customModel = state.recommendModel || '';
          if (provider === 'deepseek') {
            apiKey = state.deepseekKey || '';
            model = customModel || 'deepseek-chat';
          } else {
            apiKey = state.geminiKey || '';
            model = customModel || state.geminiModel || 'gemini-2.5-flash';
          }
        } catch { /* fall through with defaults */ }

        if (!apiKey) {
          // No credentials configured — select all
          setSelectedCharIds(characters.map(c => c.id));
          setSelectedSettingIds(settings.map(s => s.id));
          setRecommending(false);
          return;
        }

        const resp = await api.generateAI({
          novel_id: novelId,
          action: 'recommend',
          instruction,
          provider,
          model,
          api_key: apiKey,
        });

        const reader = resp.body?.getReader();
        const decoder = new TextDecoder();
        let full = '';
        let errorMsg = '';
        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            for (const line of decoder.decode(value, { stream: true }).split('\n')) {
              if (line.startsWith('data: ') && line.slice(6).trim() !== '[DONE]') {
                try {
                  const parsed = JSON.parse(line.slice(6).trim());
                  if (parsed.error) {
                    errorMsg = parsed.error;
                  } else if (parsed.token) {
                    full += parsed.token;
                  }
                } catch {}
              }
            }
          }
        }

        if (errorMsg) {
          console.error('Recommend error:', errorMsg);
          setSelectedCharIds(characters.map(c => c.id));
          setSelectedSettingIds(settings.map(s => s.id));
          setRecommending(false);
          return;
        }

        // Parse JSON from response
        const match = full.match(/\{[\s\S]*\}/);
        if (match) {
          const parsed = JSON.parse(match[0]);
          const charIds: number[] = Array.isArray(parsed.character_ids) ? parsed.character_ids : [];
          const setIds: number[] = Array.isArray(parsed.setting_ids) ? parsed.setting_ids : [];
          // Filter to only valid IDs that exist
          const validCharIds = charIds.filter(id => typeof id === 'number' && characters.some(c => c.id === id));
          const validSetIds = setIds.filter(id => typeof id === 'number' && settings.some(s => s.id === id));
          if (validCharIds.length || validSetIds.length) {
            setSelectedCharIds(validCharIds);
            setSelectedSettingIds(validSetIds);
          } else {
            // AI returned nothing useful — select all as fallback
            setSelectedCharIds(characters.map(c => c.id));
            setSelectedSettingIds(settings.map(s => s.id));
          }
        } else {
          // No JSON found — select all
          setSelectedCharIds(characters.map(c => c.id));
          setSelectedSettingIds(settings.map(s => s.id));
        }
      } catch {
        setSelectedCharIds(characters.map(c => c.id));
        setSelectedSettingIds(settings.map(s => s.id));
      }
      setRecommending(false);
    };
    doRecommend();
  }, [characters, settings, sectionTitle, sectionSummary, sectionId, novelId, recommending]);

  const filteredChars = characters.filter(c =>
    c.name.toLowerCase().includes(charSearch.toLowerCase()) && !selectedCharIds.includes(c.id)
  );
  const filteredSettings = settings.filter(s =>
    s.name.toLowerCase().includes(settingSearch.toLowerCase()) && !selectedSettingIds.includes(s.id)
  );

  const selectedChars = characters.filter(c => selectedCharIds.includes(c.id));
  const selectedWorldSettings = settings.filter(s => selectedSettingIds.includes(s.id));

  const handleEditChar = (char: Character) => {
    const p = char.profile || {};
    setEditCharForm({ name: char.name, age: p.age || '', personality: p.personality || '', background: p.background || '', appearance: p.appearance || '', speech_style: p.speech_style || '', arc: char.arc || '' });
    setEditingChar(char);
    setEditingSetting(null);
  };

  const saveEditChar = async () => {
    if (!editingChar) return;
    const name = editCharForm.name || editingChar.name;
    const arc = editCharForm.arc || '';
    const profile = { age: editCharForm.age || '', personality: editCharForm.personality || '', background: editCharForm.background || '', appearance: editCharForm.appearance || '', speech_style: editCharForm.speech_style || '' };
    await api.updateCharacter(editingChar.id, { name, arc, profile });
    setEditingChar(null);
    loadCharacters();
  };

  const handleEditSetting = (s: Setting) => {
    setEditingSetting(s);
    setEditingChar(null);
  };

  const saveEditSetting = async () => {
    if (!editingSetting) return;
    await api.updateSetting(editingSetting.id, { description: editingSetting.description });
    setEditingSetting(null);
    loadSettings();
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl w-full max-w-3xl mx-4 p-6 border border-zinc-200 dark:border-zinc-700 max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 mb-4">创作准备</h2>

        {recommending ? (
          <div className="flex-1 flex items-center justify-center py-12">
            <div className="text-center">
              <Loader2 size={32} className="animate-spin text-indigo-500 mx-auto mb-3" />
              <p className="text-sm text-zinc-500">AI 正在根据大纲推荐相关角色和设定…</p>
              <p className="text-xs text-zinc-400 mt-1">请稍候，可以稍后手动调整选择</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 grid grid-cols-2 gap-4 overflow-hidden">
          {/* Left: Characters */}
          <div className="flex flex-col overflow-hidden">
            <h3 className="text-sm font-semibold text-indigo-600 dark:text-indigo-400 mb-2">选择角色</h3>
            <div className="flex items-center border rounded-lg mb-2">
              <Search size={14} className="ml-2 text-zinc-400" />
              <input value={charSearch} onChange={(e) => setCharSearch(e.target.value)} placeholder="搜索角色…"
                className="w-full px-2 py-1.5 text-sm bg-transparent text-zinc-900 dark:text-zinc-100 outline-none" />
            </div>

            {selectedChars.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {selectedChars.map(c => (
                  <span key={c.id} className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400 rounded-full">
                    {c.name}
                    <button onClick={() => setSelectedCharIds(p => p.filter(id => id !== c.id))} className="hover:text-red-500">&times;</button>
                  </span>
                ))}
              </div>
            )}

            {editingChar && (
              <div className="mb-2 p-3 bg-indigo-50/50 dark:bg-indigo-900/10 rounded-lg space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-indigo-700">编辑 {editingChar.name}</span>
                  <button onClick={() => setEditingChar(null)} className="text-zinc-400 hover:text-red-500"><X size={14} /></button>
                </div>
                <input value={editCharForm.name} onChange={e => setEditCharForm({...editCharForm, name: e.target.value})} placeholder="姓名" className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-800" />
                <input value={editCharForm.age} onChange={e => setEditCharForm({...editCharForm, age: e.target.value})} placeholder="年龄" className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-800" />
                <input value={editCharForm.personality} onChange={e => setEditCharForm({...editCharForm, personality: e.target.value})} placeholder="性格" className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-800" />
                <input value={editCharForm.appearance} onChange={e => setEditCharForm({...editCharForm, appearance: e.target.value})} placeholder="外貌" className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-800" />
                <input value={editCharForm.background} onChange={e => setEditCharForm({...editCharForm, background: e.target.value})} placeholder="背景" className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-800" />
                <input value={editCharForm.speech_style} onChange={e => setEditCharForm({...editCharForm, speech_style: e.target.value})} placeholder="说话风格" className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-800" />
                <textarea value={editCharForm.arc} onChange={e => setEditCharForm({...editCharForm, arc: e.target.value})} placeholder="角色弧光" rows={2} className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-800 resize-none" />
                <button onClick={saveEditChar} className="text-xs px-2 py-1 bg-indigo-600 text-white rounded cursor-pointer">保存</button>
              </div>
            )}

            <div className="flex-1 overflow-y-auto space-y-1">
              {filteredChars.map(c => (
                <div key={c.id} className="flex items-center gap-1 px-2 py-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-sm text-zinc-700 dark:text-zinc-300 cursor-pointer"
                  onClick={() => setSelectedCharIds(p => [...p, c.id])}>
                  <span className="flex-1">{c.name}</span>
                  <button onClick={(e) => { e.stopPropagation(); handleEditChar(c); }} className="p-0.5 text-zinc-400 hover:text-indigo-500"><Edit3 size={11} /></button>
                </div>
              ))}
              {charSearch && filteredChars.length === 0 && <p className="text-xs text-zinc-400 px-2">无匹配角色</p>}
            </div>
          </div>

          {/* Right: Settings */}
          <div className="flex flex-col overflow-hidden">
            <h3 className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-2">选择世界观</h3>
            <div className="flex items-center border rounded-lg mb-2">
              <Search size={14} className="ml-2 text-zinc-400" />
              <input value={settingSearch} onChange={(e) => setSettingSearch(e.target.value)} placeholder="搜索设定…"
                className="w-full px-2 py-1.5 text-sm bg-transparent text-zinc-900 dark:text-zinc-100 outline-none" />
            </div>

            {selectedWorldSettings.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-2">
                {selectedWorldSettings.map(s => (
                  <span key={s.id} className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 rounded-full">
                    {s.name}
                    <button onClick={() => setSelectedSettingIds(p => p.filter(id => id !== s.id))} className="hover:text-red-500">&times;</button>
                  </span>
                ))}
              </div>
            )}

            {editingSetting && (
              <div className="mb-2 p-3 bg-emerald-50/50 dark:bg-emerald-900/10 rounded-lg space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-emerald-700">编辑 {editingSetting.name}</span>
                  <button onClick={() => setEditingSetting(null)} className="text-zinc-400 hover:text-red-500"><X size={14} /></button>
                </div>
                <textarea value={editingSetting.description} onChange={e => setEditingSetting({...editingSetting, description: e.target.value})} placeholder="描述…" rows={3}
                  className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-800 resize-none" />
                <button onClick={saveEditSetting} className="text-xs px-2 py-1 bg-indigo-600 text-white rounded cursor-pointer">保存</button>
              </div>
            )}

            <div className="flex-1 overflow-y-auto space-y-1">
              {filteredSettings.map(s => (
                <div key={s.id} className="flex items-center gap-1 px-2 py-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-sm text-zinc-700 dark:text-zinc-300 cursor-pointer"
                  onClick={() => setSelectedSettingIds(p => [...p, s.id])}>
                  <span className="flex-1">{s.name}</span>
                  <button onClick={(e) => { e.stopPropagation(); handleEditSetting(s); }} className="p-0.5 text-zinc-400 hover:text-indigo-500"><Edit3 size={11} /></button>
                </div>
              ))}
              {settingSearch && filteredSettings.length === 0 && <p className="text-xs text-zinc-400 px-2">无匹配设定</p>}
            </div>
          </div>
        </div>
        )}

        <div className="flex gap-2 mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-700">
          <button onClick={onClose} className="flex-1 px-3 py-2 text-sm rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-400 cursor-pointer">取消</button>
          <button onClick={() => onStart(sectionId, selectedCharIds, selectedSettingIds)}
            className="flex-1 px-3 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer flex items-center justify-center gap-1.5">
            <Wand2 size={14} />开始写作
          </button>
        </div>
      </div>
    </div>
  );
}
