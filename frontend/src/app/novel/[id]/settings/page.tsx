"use client";

import { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Plus, Trash2, Edit3, MapPin, Swords, BookOpen, Users, Gem, Clock, Award } from 'lucide-react';
import { useCurrentNovelStore } from '@/store';
import { api } from '@/lib/api';
import type { Setting } from '@/types';

const CATEGORIES = [
  { key: 'location', label: '环境场景', icon: MapPin, color: 'emerald',
    types: ['自然环境', '社会环境'] },
  { key: 'faction', label: '势力组织', icon: Swords, color: 'red',
    types: ['国家', '宗门', '商会', '军队', '帮派', '学院', '其他'] },
  { key: 'rule', label: '世界观规则', icon: BookOpen, color: 'amber',
    types: [] },
  { key: 'race', label: '种族物种', icon: Users, color: 'purple',
    types: ['动植物', '魔物', '传说生物', '智慧种族'] },
  { key: 'item', label: '重要物品', icon: Gem, color: 'sky',
    types: ['武器', '神器', '道具', '载具', '文献', '其他'] },
  { key: 'profession', label: '职业', icon: Award, color: 'indigo',
    types: [] },
  { key: 'history', label: '历史事件', icon: Clock, color: 'orange',
    types: ['战争', '灾难', '发现', '革命', '其他'] },
];

export default function SettingsPage() {
  const params = useParams();
  const router = useRouter();
  const novelId = Number(params.id);
  const { settings, loadSettings, novel, loadNovel, notFound } = useCurrentNovelStore();
  const [activeCategory, setActiveCategory] = useState('location');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ name: '', category: 'location', location_type: '', description: '' });
  const [formFeatures, setFormFeatures] = useState('');

  useEffect(() => { loadNovel(novelId); loadSettings(); }, [novelId]);
  useEffect(() => { if (notFound) router.push('/'); }, [notFound, router]);

  const activeCat = CATEGORIES.find(c => c.key === activeCategory)!;
  const filteredSettings = settings.filter((s: Setting) => s.category === activeCategory);

  const catCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    settings.forEach((s: Setting) => {
      counts[s.category] = (counts[s.category] || 0) + 1;
    });
    return counts;
  }, [settings]);

  const resetForm = () => {
    setForm({ name: '', category: activeCategory, location_type: '', description: '' });
    setFormFeatures('');
    setEditingId(null);
    setShowForm(false);
  };

  const handleEdit = (s: Setting) => {
    setForm({
      name: s.name,
      category: s.category,
      location_type: s.location_type,
      description: s.description,
    });
    setFormFeatures((s.notable_features || []).join('\n'));
    setEditingId(s.id);
    setShowForm(true);
  };

  const handleNew = () => {
    setForm({ name: '', category: activeCategory, location_type: '', description: '' });
    setFormFeatures('');
    setEditingId(null);
    setShowForm(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    const features = formFeatures
      .split('\n')
      .map(f => f.trim())
      .filter(Boolean);

    const data = { ...form, name: form.name.trim(), notable_features: features };

    if (editingId) {
      await api.updateSetting(editingId, data);
    } else {
      await api.createSetting({ novel_id: novelId, ...data });
    }
    resetForm();
    loadSettings();
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除？')) return;
    await api.deleteSetting(id);
    loadSettings();
  };

  const colorMap: Record<string, string> = {
    emerald: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400',
    red: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    amber: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
    purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
    sky: 'bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-400',
    orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400',
    indigo: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400',
  };

  const raceSubtypeColors: Record<string, string> = {
    '动植物':   'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
    '魔物':     'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    '传说生物': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    '智慧种族': 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
  };

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">世界观设定</h1>
        <button
          onClick={handleNew}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer"
        >
          <Plus size={14} />
          新建{activeCat.label}
        </button>
      </div>

      {/* Category tabs */}
      <div className="flex gap-1.5 mb-6 overflow-x-auto pb-1">
        {CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const count = catCounts[cat.key] || 0;
          const active = activeCategory === cat.key;
          return (
            <button
              key={cat.key}
              onClick={() => {
                setActiveCategory(cat.key);
                resetForm();
              }}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm whitespace-nowrap transition-colors cursor-pointer ${
                active
                  ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-medium'
                  : 'bg-white dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-700 border border-zinc-200 dark:border-zinc-700'
              }`}
            >
              <Icon size={14} />
              {cat.label}
              {count > 0 && (
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                  active
                    ? 'bg-white/20 text-white dark:text-zinc-900 dark:bg-zinc-300'
                    : 'bg-zinc-100 dark:bg-zinc-700'
                }`}>
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Create / Edit form */}
      {showForm && (
        <form onSubmit={handleSave} className="mb-6 p-5 bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 space-y-3">
          <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">
            {editingId ? `编辑${activeCat.label}` : `新建${activeCat.label}`}
          </h3>
          <div className={`grid ${activeCat.types.length > 0 ? 'grid-cols-3' : 'grid-cols-1'} gap-3`}>
            <div className={activeCat.types.length > 0 ? 'col-span-2' : ''}>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="名称"
                className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
                autoFocus
              />
            </div>
            {activeCat.types.length > 0 && (
            <select
              value={form.location_type}
              onChange={(e) => setForm({ ...form, location_type: e.target.value })}
              className="px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            >
              <option value="">选择子类型...</option>
              {activeCat.types.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            )}
          </div>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="描述..."
            rows={3}
            className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100 resize-none"
          />
          <textarea
            value={formFeatures}
            onChange={(e) => setFormFeatures(e.target.value)}
            placeholder={activeCat.key === 'profession'
              ? '例如：剑术精通 S、火焰魔法 A、潜行 B…（每行一项）'
              : '关键特征/规则（每行一项）'}
            rows={activeCat.key === 'profession' ? 4 : 2}
            className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100 resize-none text-sm"
          />
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={resetForm} className="px-3 py-1.5 text-sm rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 cursor-pointer">取消</button>
            <button type="submit" disabled={!form.name.trim()} className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 cursor-pointer">保存</button>
          </div>
        </form>
      )}

      {/* Settings grid */}
      {filteredSettings.length === 0 ? (
        <div className="text-center py-16 text-zinc-400">
          <p>还没有{activeCat.label}设定</p>
          <button onClick={handleNew} className="mt-2 text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            点击创建
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filteredSettings.map((s: Setting) => (
            <div key={s.id} className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-5 relative group hover:border-zinc-300 dark:hover:border-zinc-600 transition-colors">
              <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${colorMap[activeCat.color] || ''}`}>
                  {(() => {
                    const CatIcon = activeCat.icon;
                    return <CatIcon size={16} />;
                  })()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">{s.name}</h3>
                    {s.location_type && (
                      <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                        activeCat.key === 'race' ? (raceSubtypeColors[s.location_type] || 'bg-zinc-100 dark:bg-zinc-700 text-zinc-500')
                        : (colorMap[activeCat.color] || 'bg-zinc-100 dark:bg-zinc-700 text-zinc-500')
                      }`}>
                        {s.location_type}
                      </span>
                    )}
                  </div>
                  {s.description && (
                    <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-2 line-clamp-3">
                      {s.description}
                    </p>
                  )}
                  {s.notable_features?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {activeCat.key === 'profession' && (
                        <span className="block w-full text-xs text-zinc-400 mb-1 font-medium">能力</span>
                      )}
                      {s.notable_features.map((f, i) => (
                        <span key={i} className="text-xs px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-700 rounded text-zinc-500">
                          {f}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => handleEdit(s)} className="p-1 text-zinc-400 hover:text-indigo-500 cursor-pointer">
                  <Edit3 size={14} />
                </button>
                <button onClick={() => handleDelete(s.id)} className="p-1 text-zinc-400 hover:text-red-500 cursor-pointer">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
