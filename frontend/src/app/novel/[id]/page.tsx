"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Edit3, ChevronRight, ChevronDown, FileText, PenLine } from 'lucide-react';
import { useCurrentNovelStore } from '@/store';
import type { OutlineNode } from '@/types';

export default function NovelOverviewPage() {
  const params = useParams();
  const router = useRouter();
  const novelId = Number(params.id);
  const { novel, loading, notFound, loadNovel } = useCurrentNovelStore();
  const { outline, loadOutline } = useCurrentNovelStore();
  const [editingNovel, setEditingNovel] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editGenre, setEditGenre] = useState('');
  const [editStyle, setEditStyle] = useState('');
  const [expandedVolumes, setExpandedVolumes] = useState<Set<number>>(new Set());
  const [expandedChapters, setExpandedChapters] = useState<Set<number>>(new Set());

  useEffect(() => { loadNovel(novelId); loadOutline(); }, [novelId]);
  useEffect(() => { if (notFound) router.push('/'); }, [notFound, router]);
  useEffect(() => {
    if (outline.length) {
      const vIds = new Set(outline.map(v => v.id));
      setExpandedVolumes(vIds);
      const chIds = new Set<number>();
      outline.forEach(v => v.children?.forEach(ch => chIds.add(ch.id)));
      setExpandedChapters(chIds);
    }
  }, [outline]);

  const toggle = (setter: typeof setExpandedVolumes, id: number) => {
    setter(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  };

  const labels: Record<string, string> = { volume: '卷', chapter: '章', scene: '节' };
  const colors: Record<string, string> = { volume: 'text-purple-500', chapter: 'text-blue-500', scene: 'text-green-500' };

  if (loading || !novel) return <div className="p-8 text-zinc-500">加载中...</div>;

  return (
    <div className="max-w-4xl mx-auto p-8">
      {/* Novel Header */}
      <div className="mb-8">
        {editingNovel ? (
          <div className="bg-white dark:bg-zinc-800 p-6 rounded-xl border border-zinc-200 dark:border-zinc-700 space-y-3">
            <input value={editTitle} onChange={e => setEditTitle(e.target.value)} className="w-full text-xl font-bold px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100" />
            <input value={editGenre} onChange={e => setEditGenre(e.target.value)} placeholder="类型" className="w-full px-3 py-2 border rounded-lg bg-transparent" />
            <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} placeholder="简介" rows={2} className="w-full px-3 py-2 border rounded-lg bg-transparent resize-none" />
            <textarea value={editStyle} onChange={e => setEditStyle(e.target.value)} placeholder="写作风格" rows={2} className="w-full px-3 py-2 border rounded-lg bg-transparent resize-none" />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setEditingNovel(false)} className="px-4 py-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 cursor-pointer">取消</button>
              <button onClick={async () => { const { api } = await import('@/lib/api'); await api.updateNovel(novelId, { title: editTitle, description: editDesc, genre: editGenre, style_notes: editStyle }); setEditingNovel(false); loadNovel(novelId); }} className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer">保存</button>
            </div>
          </div>
        ) : (
          <div className="group">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">{novel.title}</h1>
                <div className="flex gap-4 mt-2 text-sm text-zinc-500">{novel.genre && <span>{novel.genre}</span>}<span>{novel.total_word_count.toLocaleString()} 字</span></div>
                {novel.description && <p className="mt-3 text-zinc-600 dark:text-zinc-400">{novel.description}</p>}
                {novel.style_notes && <div className="mt-2 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg text-sm text-amber-800 dark:text-amber-300"><span className="font-medium">写作风格：</span>{novel.style_notes}</div>}
              </div>
              <button onClick={() => { setEditTitle(novel.title); setEditDesc(novel.description); setEditGenre(novel.genre); setEditStyle(novel.style_notes); setEditingNovel(true); }} className="p-2 text-zinc-400 hover:text-indigo-600 opacity-0 group-hover:opacity-100 transition-all cursor-pointer"><Edit3 size={16} /></button>
            </div>
          </div>
        )}
      </div>

      {/* Outline Progress Tree */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">大纲</h2>
          <button onClick={() => router.push(`/novel/${novelId}/outline`)} className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">编辑大纲 →</button>
        </div>

        {outline.length === 0 ? (
          <p className="text-zinc-400 dark:text-zinc-500 text-sm">还没有大纲，开始规划你的故事吧</p>
        ) : (
          <div className="space-y-0.5">
            {outline.map((vol: OutlineNode) => {
              const vExpanded = expandedVolumes.has(vol.id);
              return (
                <div key={vol.id}>
                  <button onClick={() => toggle(setExpandedVolumes, vol.id)} className="flex items-center gap-1.5 py-2 px-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 w-full text-left cursor-pointer">
                    {vExpanded ? <ChevronDown size={14} className="text-zinc-400" /> : <ChevronRight size={14} className="text-zinc-400" />}
                    <FileText size={14} className={colors.volume} />
                    <span className="text-sm font-semibold">{vol.title}</span>
                    {vol.summary && <span className="text-xs text-zinc-400 truncate">— {vol.summary}</span>}
                  </button>
                  {vExpanded && (vol.children || []).map((ch: OutlineNode) => {
                    const chExpanded = expandedChapters.has(ch.id);
                    return (
                      <div key={ch.id}>
                        <button onClick={() => toggle(setExpandedChapters, ch.id)} className="flex items-center gap-1.5 py-1.5 pl-10 pr-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 w-full text-left cursor-pointer">
                          {chExpanded ? <ChevronDown size={12} className="text-zinc-400" /> : <ChevronRight size={12} className="text-zinc-400" />}
                          <FileText size={12} className={colors.chapter} />
                          <span className="text-sm text-zinc-700 dark:text-zinc-300">{ch.title}</span>
                          {ch.summary && <span className="text-xs text-zinc-400 truncate">— {ch.summary}</span>}
                        </button>
                        {chExpanded && (ch.children || []).map((sec: OutlineNode) => (
                          <div key={sec.id} onClick={() => router.push(`/novel/${novelId}/section/${sec.id}`)}
                            className="flex items-center gap-1.5 py-1.5 pl-20 pr-3 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer group">
                            <ChevronRight size={12} className="text-zinc-300 group-hover:text-indigo-500" />
                            <span className="text-sm text-zinc-600 dark:text-zinc-400">{sec.title}</span>
                            {sec.summary && <span className="text-xs text-zinc-400 truncate max-w-[150px] hidden sm:inline">— {sec.summary}</span>}
                            <span className="text-xs text-zinc-400 ml-auto">
                              {sec.content ? `${sec.content.replace(/<[^>]+>/g, '').length} 字` : <span className="text-zinc-300">未开始</span>}
                            </span>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
