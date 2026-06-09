"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Plus, Trash2, Edit3, Link as LinkIcon, X } from 'lucide-react';
import { useCurrentNovelStore } from '@/store';
import { api } from '@/lib/api';
import type { Character, CharacterProfile, Relationship } from '@/types';

const PROFILE_FIELDS: { key: keyof CharacterProfile; label: string }[] = [
  { key: 'appearance', label: '外貌' },
  { key: 'age', label: '年龄' },
  { key: 'personality', label: '性格' },
  { key: 'background', label: '背景' },
  { key: 'speech_style', label: '说话风格' },
];

export default function CharactersPage() {
  const params = useParams();
  const router = useRouter();
  const novelId = Number(params.id);
  const { characters, loadCharacters, novel, loadNovel, notFound } = useCurrentNovelStore();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<{ name: string; role: Character['role']; arc: string }>({ name: '', role: 'supporting', arc: '' });
  const [profileForm, setProfileForm] = useState<CharacterProfile>({});
  const [showRelation, setShowRelation] = useState<number | null>(null);
  const [relTarget, setRelTarget] = useState(0);
  const [relType, setRelType] = useState('');
  const [relDesc, setRelDesc] = useState('');

  useEffect(() => { loadNovel(novelId); loadCharacters(); }, [novelId]);
  useEffect(() => { if (notFound) router.push('/'); }, [notFound, router]);

  const resetForm = () => {
    setForm({ name: '', role: 'supporting', arc: '' });
    setProfileForm({});
    setEditingId(null);
    setShowForm(false);
  };

  const handleEdit = (c: Character) => {
    setForm({ name: c.name, role: c.role, arc: c.arc });
    setProfileForm(c.profile || {});
    setEditingId(c.id);
    setShowForm(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    if (editingId) {
      await api.updateCharacter(editingId, { ...form, profile: profileForm });
    } else {
      await api.createCharacter({
        novel_id: novelId,
        name: form.name.trim(),
        role: form.role as Character['role'],
        profile: profileForm,
        arc: form.arc,
        avatar_color: `#${Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0')}`,
        aliases: [],
      });
    }
    resetForm();
    loadCharacters();
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除这个角色？')) return;
    await api.deleteCharacter(id);
    loadCharacters();
  };

  const handleAddRelation = async () => {
    if (!relTarget || !relType.trim()) return;
    await api.createRelationship({
      source_id: showRelation!,
      target_id: relTarget,
      relation_type: relType,
      description: relDesc,
    });
    setShowRelation(null);
    setRelTarget(0);
    setRelType('');
    setRelDesc('');
    loadCharacters();
  };

  const handleDeleteRelation = async (id: number) => {
    await api.deleteRelationship(id);
    loadCharacters();
  };

  const roleLabels: Record<string, string> = {
    protagonist: '主角',
    antagonist: '反派',
    supporting: '配角',
    minor: '次要',
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">角色管理</h1>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 cursor-pointer"
        >
          <Plus size={14} />
          新建角色
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSave} className="mb-6 p-5 bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 space-y-3">
          <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">
            {editingId ? '编辑角色' : '新建角色'}
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="角色姓名"
              className="px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
              autoFocus
            />
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as Character['role'] })}
              className="px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            >
              {Object.entries(roleLabels).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
          </div>
          {PROFILE_FIELDS.map(({ key, label }) => (
            <input
              key={key}
              value={profileForm[key] || ''}
              onChange={(e) => setProfileForm({ ...profileForm, [key]: e.target.value })}
              placeholder={label}
              className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
            />
          ))}
          <input
            value={form.arc}
            onChange={(e) => setForm({ ...form, arc: e.target.value })}
            placeholder="角色弧光（角色在故事中的成长变化）"
            className="w-full px-3 py-2 border rounded-lg bg-transparent text-zinc-900 dark:text-zinc-100"
          />
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={resetForm} className="px-3 py-1.5 text-sm rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-700 cursor-pointer">取消</button>
            <button type="submit" disabled={!form.name.trim()} className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 cursor-pointer">保存</button>
          </div>
        </form>
      )}

      {characters.length === 0 ? (
        <div className="text-center py-16 text-zinc-400">
          <p>还没有角色，从"新建角色"开始创建</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {characters.map((c: Character) => (
            <div key={c.id} className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-5 relative group">
              <div className="flex items-start gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
                  style={{ backgroundColor: c.avatar_color }}
                >
                  {c.name[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">{c.name}</h3>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-700 text-zinc-500">
                      {roleLabels[c.role] || c.role}
                    </span>
                  </div>
                  {c.profile?.personality && (
                    <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1 line-clamp-1">
                      {c.profile.personality}
                    </p>
                  )}
                  {c.arc && (
                    <p className="text-xs text-indigo-500 dark:text-indigo-400 mt-1 line-clamp-1">
                      弧光：{c.arc}
                    </p>
                  )}
                  {c.relationships.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {c.relationships.map((r: Relationship) => (
                        <span
                          key={r.id}
                          className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-zinc-100 dark:bg-zinc-700 rounded-full group/rel cursor-default"
                        >
                          {r.target_name || r.relation_type}
                          <button
                            onClick={() => handleDeleteRelation(r.id)}
                            className="opacity-0 group-hover/rel:opacity-100 text-zinc-400 hover:text-red-500"
                          >
                            <X size={10} />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => setShowRelation(c.id)} className="p-1 text-zinc-400 hover:text-indigo-500 cursor-pointer" title="添加关系">
                  <LinkIcon size={14} />
                </button>
                <button onClick={() => handleEdit(c)} className="p-1 text-zinc-400 hover:text-indigo-500 cursor-pointer">
                  <Edit3 size={14} />
                </button>
                <button onClick={() => handleDelete(c.id)} className="p-1 text-zinc-400 hover:text-red-500 cursor-pointer">
                  <Trash2 size={14} />
                </button>
              </div>

              {/* Relationship form */}
              {showRelation === c.id && (
                <div className="mt-3 p-3 bg-zinc-50 dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-700">
                  <p className="text-xs text-zinc-500 mb-2">添加关系（{c.name}）</p>
                  <select
                    value={relTarget}
                    onChange={(e) => setRelTarget(Number(e.target.value))}
                    className="w-full px-2 py-1.5 mb-2 border rounded text-sm bg-transparent text-zinc-900 dark:text-zinc-100"
                  >
                    <option value={0}>选择关联角色...</option>
                    {characters.filter(ch => ch.id !== c.id).map(ch => (
                      <option key={ch.id} value={ch.id}>{ch.name}</option>
                    ))}
                  </select>
                  <input
                    value={relType}
                    onChange={(e) => setRelType(e.target.value)}
                    placeholder="关系（如：师徒、恋人、敌人）"
                    className="w-full px-2 py-1.5 mb-2 border rounded text-sm bg-transparent text-zinc-900 dark:text-zinc-100"
                  />
                  <input
                    value={relDesc}
                    onChange={(e) => setRelDesc(e.target.value)}
                    placeholder="描述（可选）"
                    className="w-full px-2 py-1.5 mb-2 border rounded text-sm bg-transparent text-zinc-900 dark:text-zinc-100"
                  />
                  <div className="flex gap-2">
                    <button onClick={handleAddRelation} className="px-3 py-1 text-xs bg-indigo-600 text-white rounded cursor-pointer">确认</button>
                    <button onClick={() => setShowRelation(null)} className="px-3 py-1 text-xs rounded hover:bg-zinc-200 dark:hover:bg-zinc-700 cursor-pointer">取消</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
