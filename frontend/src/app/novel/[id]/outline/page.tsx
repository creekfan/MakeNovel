"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Plus, Trash2, ChevronRight, ChevronDown, BookOpen, PenLine, Edit3 } from 'lucide-react';
import { useCurrentNovelStore } from '@/store';
import { api } from '@/lib/api';
import PreWriteDialog from '@/components/writing/PreWriteDialog';
import type { OutlineNode } from '@/types';

function OutlineNodeItem({
  node, level,
  onUpdate, onDelete, onAddChild, onInsertChild, onStartWriting,
}: {
  node: OutlineNode;
  level: number;
  onUpdate: (id: number, data: Partial<OutlineNode>) => void;
  onDelete: (id: number) => void;
  onAddChild: (parentId: number, nodeType: string) => void;
  onInsertChild: (parentId: number, nodeType: string, sortOrder: number) => void;
  onStartWriting: (nodeId: number) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(node.title);
  const [summary, setSummary] = useState(node.summary);

  const isVolume = node.node_type === 'volume';
  const isChapter = node.node_type === 'chapter';
  const isScene = node.node_type === 'scene';

  const colors: Record<string, string> = { volume: 'text-purple-600 dark:text-purple-400', chapter: 'text-blue-600 dark:text-blue-400', scene: 'text-green-600 dark:text-green-400' };
  const labels: Record<string, string> = { volume: '卷', chapter: '章', scene: '节' };
  const bgColors: Record<string, string> = { volume: 'bg-purple-50 dark:bg-purple-900/10', chapter: 'bg-blue-50 dark:bg-blue-900/10', scene: '' };

  return (
    <div className={bgColors[node.node_type] || ''}>
      <div className="flex items-center gap-1.5 py-1.5 px-2 rounded-lg hover:bg-zinc-100/50 dark:hover:bg-zinc-800/50 group" style={{ paddingLeft: `${level * 24 + 8}px` }}>
        {node.children.length > 0 && (
          <button onClick={() => setExpanded(!expanded)} className="p-0.5 text-zinc-400 hover:text-zinc-600 cursor-pointer shrink-0">
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        )}
        {node.children.length === 0 && <span className="w-5 shrink-0" />}

        {editing ? (
          <div className="flex-1 flex flex-col gap-1">
            <div className="flex gap-2">
              <input value={title} onChange={(e) => setTitle(e.target.value)}
                className="flex-1 px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100" autoFocus />
              <button onClick={() => { onUpdate(node.id, { title, summary }); setEditing(false); }}
                className="text-xs px-2 py-1 bg-indigo-600 text-white rounded cursor-pointer shrink-0">保存</button>
            </div>
            {(isVolume || isChapter) && (
              <textarea value={summary} onChange={(e) => setSummary(e.target.value)}
                placeholder={isVolume ? '主题描述…' : '章节描述…'} rows={1}
                className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 resize-none" />
            )}
            {isScene && (
              <textarea value={summary} onChange={(e) => setSummary(e.target.value)}
                placeholder="情节概要…" rows={1}
                className="w-full px-2 py-1 text-xs border rounded bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 resize-none" />
            )}
          </div>
        ) : (
          <div className="flex-1 min-w-0 flex items-baseline gap-1.5">
            <span className={`text-[10px] font-mono ${colors[node.node_type] || 'text-zinc-500'} shrink-0`}>[{labels[node.node_type]}]</span>
            <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200 cursor-pointer hover:text-indigo-600 dark:hover:text-indigo-400"
              onClick={() => { setTitle(node.title); setSummary(node.summary); setEditing(true); }}>
              {node.title}
            </span>
            {node.summary && !isScene && <span className="text-xs text-zinc-400 truncate hidden sm:inline">— {node.summary}</span>}
          </div>
        )}
        <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity ml-auto shrink-0">
          {(isVolume || isChapter) && (
            <button onClick={() => onAddChild(node.id, isVolume ? 'chapter' : 'scene')}
              className="p-1 text-zinc-400 hover:text-indigo-500 cursor-pointer" title={isVolume ? '添加章' : '添加节'}>
              <Plus size={12} />
            </button>
          )}
          <button onClick={() => onDelete(node.id)} className="p-1 text-zinc-400 hover:text-red-500 cursor-pointer"><Trash2 size={12} /></button>
        </div>
      </div>

      {/* Always show content when expanded (not just in edit) */}
      {expanded && (
        <div style={{ paddingLeft: `${level * 24 + 28}px` }}>
          {isScene && node.summary && !editing && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-1 pl-1">情节：{node.summary}</p>
          )}
          {isScene && (
            <div className="flex items-center gap-2 py-0.5 mb-1">
              {node.content ? (
                <span className="text-xs text-zinc-400">{node.content.replace(/<[^>]+>/g, '').length} 字已写</span>
              ) : <span className="text-xs text-zinc-400">尚未开始</span>}
              <button onClick={() => onStartWriting(node.id)}
                className="flex items-center gap-1 text-xs px-2 py-0.5 bg-indigo-600 text-white rounded hover:bg-indigo-700 cursor-pointer">
                <PenLine size={10} />开始创作
              </button>
            </div>
          )}

          {node.children.length > 0 && (
            <div>
              {node.children.map((child, idx) => (
                <div key={child.id}>
                  {/* Insert button between children */}
                  {(isVolume || isChapter) && (
                    <div className="flex items-center opacity-30 hover:opacity-100 transition-opacity" style={{ paddingLeft: `${(level + 1) * 24 + 8}px` }}>
                      <button onClick={() => {
                        const prev = node.children[idx - 1];
                        const prevSO = prev?.sort_order || 0;
                        const curSO = child.sort_order || 0;
                        let so: number;
                        if (prev) {
                          so = (prevSO + curSO) / 2;
                          if (so <= prevSO || so >= curSO) so = prevSO + 0.5;
                        } else {
                          so = curSO - 1;
                        }
                        onInsertChild(node.id, isVolume ? 'chapter' : 'scene', so);
                      }}
                        className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-indigo-500 py-0.5 cursor-pointer">
                        <Plus size={8} />在此处插入{isVolume ? '章' : '节'}
                      </button>
                    </div>
                  )}
                  <OutlineNodeItem node={child} level={level + 1}
                    onUpdate={onUpdate} onDelete={onDelete} onAddChild={onAddChild}
                    onInsertChild={onInsertChild} onStartWriting={onStartWriting} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function OutlinePage() {
  const params = useParams();
  const router = useRouter();
  const novelId = Number(params.id);
  const { outline, loadOutline, loadCharacters, loadSettings, novel, loadNovel, notFound } = useCurrentNovelStore();
  const [showAdd, setShowAdd] = useState<'volume' | 'chapter' | null>(null);
  const [parentId, setParentId] = useState<number | null>(null);
  const [formTitle, setFormTitle] = useState('');
  const [formSummary, setFormSummary] = useState('');
  const [formSortOrder, setFormSortOrder] = useState<number | null>(null);
  const [preWriteNodeId, setPreWriteNodeId] = useState<number | null>(null);

  useEffect(() => { loadNovel(novelId); loadOutline(); loadCharacters(); loadSettings(); }, [novelId]);
  useEffect(() => { if (notFound) router.push('/'); }, [notFound, router]);

  const resetForm = () => { setShowAdd(null); setParentId(null); setFormTitle(''); setFormSummary(''); setFormSortOrder(null); };

  const handleAdd = async () => {
    if (!formTitle.trim()) return;
    const nodeType = showAdd === 'volume' ? 'volume' : 'chapter';
    const node = await api.createOutlineNode({ novel_id: novelId, parent_id: parentId, title: formTitle.trim(), summary: formSummary, node_type: nodeType, sort_order: formSortOrder ?? 0 });
    resetForm(); loadOutline();
    if (parentId) renumberChildren(parentId);
  };

  const handleInsertChild = (pid: number, nodeType: string, sortOrder: number) => {
    if (nodeType === 'chapter') { setParentId(pid); setFormSortOrder(sortOrder); setShowAdd('chapter'); }
    else if (nodeType === 'scene') { addSceneAction(pid, sortOrder); }
  };

  const handleAddChild = (pid: number, nodeType: string) => {
    if (nodeType === 'chapter') { setParentId(pid); setShowAdd('chapter'); }
    else if (nodeType === 'scene') { addSceneAction(pid); }
  };

  const addSceneAction = (pid: number, sortOrder?: number) => {
    const title = prompt('节标题：');
    if (!title?.trim()) return;
    const summary = prompt('情节概要：') || '';
    api.createOutlineNode({ novel_id: novelId, parent_id: pid, title: title.trim(), summary, node_type: 'scene', sort_order: sortOrder ?? 0 }).then(() => { loadOutline(); }).then(() => renumberChildren(pid));
  };

  const renumberChildren = async (parentId: number) => {
    const tree = await api.listOutline(novelId);
    const findChildren = (nodes: OutlineNode[]): OutlineNode[] => {
      for (const n of nodes) {
        if (n.id === parentId) return n.children || [];
        if (n.children) {
          const found = findChildren(n.children);
          if (found.length) return found;
        }
      }
      return [];
    };
    const children = findChildren(tree);
    for (let i = 0; i < children.length; i++) {
      if (children[i].sort_order !== i) {
        await api.updateOutlineNode(children[i].id, { sort_order: i });
      }
    }
  };

  const handleUpdate = async (id: number, data: Partial<OutlineNode>) => { await api.updateOutlineNode(id, data); loadOutline(); };
  const handleDelete = async (id: number) => { if (!confirm('确认删除？子节点也会被删除。')) return; await api.deleteOutlineNode(id); loadOutline(); };
  const handleStartWriting = (nodeId: number) => { setPreWriteNodeId(nodeId); };

  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">大纲规划</h1>
        <button onClick={() => { resetForm(); setShowAdd('volume'); }} className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer"><Plus size={14} />新建卷</button>
      </div>

      {showAdd && (
        <div className="mb-4 p-4 bg-white dark:bg-zinc-800 rounded-lg border border-zinc-200 dark:border-zinc-700 space-y-3">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            新建{showAdd === 'volume' ? '卷' : '章'}
          </h3>
          <input value={formTitle} onChange={(e) => setFormTitle(e.target.value)}
            placeholder={showAdd === 'volume' ? '卷名' : '章节名称'}
            className="w-full px-3 py-2 border rounded-lg bg-transparent text-sm text-zinc-900 dark:text-zinc-100" autoFocus
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()} />
          <textarea value={formSummary} onChange={(e) => setFormSummary(e.target.value)}
            placeholder={showAdd === 'volume' ? '主题描述…' : '章节描述…'} rows={2}
            className="w-full px-3 py-2 border rounded-lg bg-transparent text-sm text-zinc-900 dark:text-zinc-100 resize-none" />
          <div className="flex gap-2 justify-end">
            <button onClick={resetForm} className="px-3 py-1.5 text-sm rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 cursor-pointer">取消</button>
            <button onClick={handleAdd} disabled={!formTitle.trim()} className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 cursor-pointer">创建</button>
          </div>
        </div>
      )}

      <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-4">
        {outline.length === 0 ? (
          <div className="text-center py-12 text-zinc-400">
            <BookOpen size={32} className="mx-auto mb-2 opacity-30" />
            <p className="text-sm">还没有大纲，从"新建卷"开始规划</p>
            <button onClick={() => { resetForm(); setShowAdd('volume'); }} className="mt-2 text-xs text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">点击创建第一个卷</button>
          </div>
        ) : (
          <div>
            {outline.map((node) => (
              <OutlineNodeItem key={node.id} node={node} level={0}
                onUpdate={handleUpdate} onDelete={handleDelete}
                onAddChild={handleAddChild} onInsertChild={handleInsertChild} onStartWriting={handleStartWriting} />
            ))}
          </div>
        )}
      </div>
      <p className="mt-4 text-xs text-zinc-400">卷 → 章 → 节。在节上点击"开始创作"进入写作。</p>

      {preWriteNodeId && (
        (() => {
          const findNode = (nodes: OutlineNode[], id: number): OutlineNode | null => {
            for (const n of nodes) { if (n.id === id) return n; if (n.children) { const f = findNode(n.children, id); if (f) return f; } }
            return null;
          };
          const sec = findNode(outline, preWriteNodeId);
          return (
            <PreWriteDialog
              novelId={novelId}
              sectionId={preWriteNodeId}
              sectionTitle={sec?.title || ''}
              sectionSummary={sec?.summary || ''}
          onClose={() => setPreWriteNodeId(null)}
          onStart={(sectionId, charIds, settingIds) => {
            setPreWriteNodeId(null);
            const params = new URLSearchParams();
            if (charIds.length) params.set('chars', charIds.join(','));
            if (settingIds.length) params.set('settings', settingIds.join(','));
            const qs = params.toString();
            router.push(`/novel/${novelId}/section/${sectionId}${qs ? '?' + qs : ''}`);
          }}
        />
          );
        })()
      )}
    </div>
  );
}
