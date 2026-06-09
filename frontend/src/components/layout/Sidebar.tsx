"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { BookOpen, ListTree, Users, MapPin, Settings, Home, ChevronRight, ChevronDown, FileText } from 'lucide-react';
import { useCurrentNovelStore } from '@/store';
import type { OutlineNode } from '@/types';

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const novelMatch = pathname.match(/^\/novel\/(\d+)/);
  const novelId = novelMatch ? Number(novelMatch[1]) : null;
  const { outline, loadOutline, loadNovel } = useCurrentNovelStore();
  const [expandedNodes, setExpandedNodes] = useState<Set<number>>(new Set());

  useEffect(() => { if (novelId) { loadNovel(novelId); loadOutline(); } }, [novelId]);
  useEffect(() => {
    if (outline.length) {
      const ids = new Set<number>();
      outline.forEach(v => { ids.add(v.id); v.children?.forEach(ch => { ids.add(ch.id); ch.children?.forEach(() => {}); }); });
      setExpandedNodes(ids);
    }
  }, [outline]);

  const toggle = (id: number) => setExpandedNodes(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const links = [{ href: '/', label: '首页', icon: Home, exact: true }, { href: '/settings', label: '设置', icon: Settings, exact: true }];
  const novelLinks = novelId ? [{ href: `/novel/${novelId}`, label: '总览', icon: BookOpen }, { href: `/novel/${novelId}/outline`, label: '大纲', icon: ListTree }, { href: `/novel/${novelId}/characters`, label: '角色', icon: Users }, { href: `/novel/${novelId}/settings`, label: '世界观', icon: MapPin }] : [];

  const colors: Record<string, string> = { volume: 'text-purple-500', chapter: 'text-blue-500', scene: 'text-green-500' };

  const renderNode = (node: OutlineNode, depth: number) => {
    const isExp = expandedNodes.has(node.id);
    const hasChildren = (node.children || []).length > 0;
    const isScene = node.node_type === 'scene';
    return (
      <div key={node.id}>
        <div className="flex items-center gap-0.5 py-0.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded cursor-pointer" style={{ paddingLeft: `${depth * 12 + 4}px` }}>
          {hasChildren ? <button onClick={() => toggle(node.id)} className="p-0.5">{isExp ? <ChevronDown size={9} className="text-zinc-400" /> : <ChevronRight size={9} className="text-zinc-400" />}</button> : <span className="w-3.5" />}
          <FileText size={9} className={colors[node.node_type] || 'text-zinc-400'} />
          {isScene ? (
            <button onClick={() => router.push(`/novel/${novelId}/section/${node.id}`)} className="text-[11px] text-zinc-600 dark:text-zinc-400 truncate text-left hover:text-indigo-500 flex-1">
              {node.title}
            </button>
          ) : (
            <span className="text-[11px] font-medium truncate flex-1">{node.title}</span>
          )}
        </div>
        {isExp && hasChildren && (node.children || []).map(c => renderNode(c, depth + 1))}
      </div>
    );
  };

  return (
    <aside className="w-52 min-h-full bg-white dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800 flex flex-col shrink-0">
      <div className="p-3.5 border-b border-zinc-200 dark:border-zinc-800">
        <Link href="/" className="flex items-center gap-2"><BookOpen size={18} className="text-indigo-600" /><span className="font-bold text-sm text-zinc-900 dark:text-zinc-100">MakeNovel</span></Link>
      </div>
      <nav className="flex-1 overflow-y-auto flex flex-col">
        <div className="p-2.5 space-y-0.5 shrink-0">
          {links.map(l => { const I = l.icon; const active = l.exact ? pathname === l.href : pathname.startsWith(l.href);
            return <Link key={l.href} href={l.href} className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${active ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400 font-medium' : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'}`}><I size={14} />{l.label}</Link>;
          })}
          {novelLinks.length > 0 && <><div className="pt-1.5 pb-0.5"><div className="h-px bg-zinc-200 dark:bg-zinc-800 mb-1" /></div>
            {novelLinks.map(l => { const I = l.icon; const active = pathname === l.href;
              return <Link key={l.href} href={l.href} className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs transition-colors ${active ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400 font-medium' : 'text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'}`}><I size={14} />{l.label}</Link>;
            })}
          </>}
        </div>
        {novelId && outline.length > 0 && (
          <div className="border-t border-zinc-200 dark:border-zinc-800 p-1.5 overflow-y-auto max-h-[45vh]">
            <div className="text-[9px] font-semibold text-zinc-400 uppercase tracking-wide px-2 py-0.5">大纲</div>
            {outline.map(v => renderNode(v, 0))}
          </div>
        )}
      </nav>
    </aside>
  );
}
