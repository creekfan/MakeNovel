'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BookOpen, Plus, Trash2 } from 'lucide-react';
import { useNovelStore } from '@/store';
import type { NovelListItem } from '@/types';

export default function HomePage() {
  const router = useRouter();
  const { novels, loading, loadNovels, createNovel, deleteNovel } = useNovelStore();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [genre, setGenre] = useState('');

  useEffect(() => { loadNovels(); }, [loadNovels]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    const novel = await createNovel({ title: title.trim(), description, genre });
    setShowForm(false);
    setTitle('');
    setDescription('');
    setGenre('');
    router.push(`/novel/${novel.id}`);
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm('确认删除这部小说？所有章节和设定将被永久删除。')) return;
    await deleteNovel(id);
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">MakeNovel</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">LLM 辅助长篇小说创作工具</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors cursor-pointer"
        >
          <Plus size={18} />
          新建小说
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-8 p-6 bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700">
          <h2 className="text-lg font-semibold mb-4 text-zinc-900 dark:text-zinc-100">新建小说项目</h2>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="小说标题"
            className="w-full px-3 py-2 mb-3 border border-zinc-300 dark:border-zinc-600 rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            autoFocus
          />
          <input
            type="text"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            placeholder="类型（如：奇幻、科幻、都市）"
            className="w-full px-3 py-2 mb-3 border border-zinc-300 dark:border-zinc-600 rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="简介（可选）"
            rows={2}
            className="w-full px-3 py-2 mb-4 border border-zinc-300 dark:border-zinc-600 rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
          />
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 rounded-lg transition-colors cursor-pointer"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={!title.trim()}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors cursor-pointer"
            >
              创建
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-zinc-500 dark:text-zinc-400">加载中...</p>
      ) : novels.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen size={48} className="mx-auto text-zinc-300 dark:text-zinc-600 mb-4" />
          <p className="text-zinc-500 dark:text-zinc-400">还没有小说项目，点击"新建小说"开始创作</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {novels.map((novel: NovelListItem) => (
            <div
              key={novel.id}
              onClick={() => router.push(`/novel/${novel.id}`)}
              className="p-5 bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 hover:border-indigo-300 dark:hover:border-indigo-700 cursor-pointer transition-all group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">{novel.title}</h3>
                  {novel.description && (
                    <p className="text-zinc-500 dark:text-zinc-400 mt-1 text-sm line-clamp-2">{novel.description}</p>
                  )}
                  <div className="flex gap-4 mt-3 text-sm text-zinc-400 dark:text-zinc-500">
                    {novel.genre && <span>{novel.genre}</span>}
                    <span>{novel.chapter_count} 章</span>
                    <span>{novel.total_word_count.toLocaleString()} 字</span>
                  </div>
                </div>
                <button
                  onClick={(e) => handleDelete(e, novel.id)}
                  className="p-2 text-zinc-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all cursor-pointer"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
