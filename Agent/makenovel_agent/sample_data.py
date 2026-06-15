"""示例数据生成器 — 用于测试管道"""

import json
from pathlib import Path


def generate_all_samples(output_dir: Path):
    """生成全套示例数据"""
    output_dir.mkdir(parents=True, exist_ok=True)

    outline = _generate_outline()
    characters = _generate_characters()
    world = _generate_world()
    summaries = _generate_summaries()

    _write_json(output_dir / "outline.json", outline)
    _write_json(output_dir / "characters.json", characters)
    _write_json(output_dir / "world_settings.json", world)
    _write_json(output_dir / "summaries.json", summaries)


def _generate_outline() -> dict:
    return {
        "novel_id": "novel-001",
        "novel_title": "星辰之海",
        "volumes": [
            {
                "id": "vol-1",
                "title": "第一卷：启程",
                "node_type": "volume",
                "summary": "主角林星在边境小镇觉醒星辰之力，踏上寻找真相的旅途。",
                "status": "planned",
                "sort_order": 1.0,
                "children": [
                    {
                        "id": "ch-1",
                        "title": "第一章：觉醒之夜",
                        "node_type": "chapter",
                        "summary": "林星在流星雨之夜意外觉醒星辰之力，与神秘少女相遇。",
                        "status": "planned",
                        "sort_order": 1.0,
                        "children": [
                            {
                                "id": "sec-1-1",
                                "title": "第一节：流星雨",
                                "node_type": "section",
                                "summary": "林星独自在小镇后山观测流星雨，意外发现一颗流星坠落在附近，前往查看时触发了体内的星辰之力。",
                                "chapter_prompt": "描写林星的日常背景、性格特点，以及觉醒时的震撼感受。",
                                "status": "done",
                                "sort_order": 1.0,
                            },
                            {
                                "id": "sec-1-2",
                                "title": "第二节：神秘少女",
                                "node_type": "section",
                                "summary": "觉醒力量后，林星在陨石坑旁遇到一位受伤的神秘少女白月，两人初次交谈，少女透露林星是「星选者」。",
                                "chapter_prompt": "重点描写两人的初次相遇对话，建立悬念。",
                                "status": "planned",
                                "sort_order": 2.0,
                            },
                            {
                                "id": "sec-1-3",
                                "title": "第三节：追兵",
                                "node_type": "section",
                                "summary": "一群黑袍人追踪少女而来，林星首次使用星辰之力战斗，掩护少女逃离。",
                                "chapter_prompt": "首次战斗场景，展示林星的成长潜力和星辰之力的特性。",
                                "status": "planned",
                                "sort_order": 3.0,
                            },
                        ],
                    },
                    {
                        "id": "ch-2",
                        "title": "第二章：逃亡之路",
                        "node_type": "chapter",
                        "summary": "林星与白月逃离小镇，前往北方的星落城。途中林星开始学习控制星辰之力。",
                        "status": "planned",
                        "sort_order": 2.0,
                        "children": [
                            {
                                "id": "sec-2-1",
                                "title": "第一节：离开故乡",
                                "node_type": "section",
                                "summary": "林星告别小镇，与白月一同踏上旅途，途中白月讲解星辰之力的基本知识。",
                                "status": "planned",
                                "sort_order": 1.0,
                            },
                        ],
                    },
                ],
            }
        ],
    }


def _generate_characters() -> list[dict]:
    return [
        {
            "id": "char-lin-xing",
            "name": "林星",
            "role": "protagonist",
            "appearance": "十六岁少年，身材清瘦，黑色短发，琥珀色眼眸。常穿朴素的灰蓝色布衣。",
            "personality": "好奇心旺盛，性格温和但意志坚定。对他人的苦难充满同情，有时过于冲动。",
            "background": "边境小镇铁匠之子，母亲早逝，由父亲抚养长大。从小仰望星空，对星辰有着异于常人的感应。",
            "abilities": "星辰之力（刚觉醒，尚不稳定）——可感知和引导星光的能量。",
            "speech_style": "用词朴实，语气真挚。思考时会微微停顿。",
            "arc": "从普通少年成长为能够掌控星辰之力的强者。",
            "current_state": "刚觉醒星辰之力，身处小镇后山。",
            "relationships": [
                {
                    "source_id": "char-lin-xing",
                    "target_id": "char-bai-yue",
                    "relation_type": "同伴/导师",
                    "description": "白月是林星遇到的第一个同类，引导他了解星辰之力的世界。",
                },
                {
                    "source_id": "char-lin-xing",
                    "target_id": "char-lin-fu",
                    "relation_type": "父子",
                    "description": "林父关爱儿子但沉默寡言，对林星的天赋隐约有所察觉。",
                },
            ],
        },
        {
            "id": "char-bai-yue",
            "name": "白月",
            "role": "supporting",
            "appearance": "银白色长发，浅紫色眼眸，肌肤苍白如月。身穿残破的白色斗篷，左臂有灼伤。",
            "personality": "外表冷漠，内心温柔。因背负使命而习惯独行，对他人保持距离。",
            "background": "来自北方星落城的星选者后裔，家族被黑袍组织追杀。独自逃往南方寻找传说中的星辰之源。",
            "abilities": "月华之力——可以操控月光，擅长隐匿和幻术。",
            "speech_style": "言简意赅，语气冷淡但不失礼貌。偶尔流露出对过去的怀念。",
            "arc": "从封闭内心到重新信任他人。",
            "current_state": "受伤逃亡中，在陨石坑旁遇到林星。",
            "relationships": [
                {
                    "source_id": "char-bai-yue",
                    "target_id": "char-lin-xing",
                    "relation_type": "同伴/引导者",
                    "description": "认为林星可能是她寻找的关键人物。",
                },
            ],
        },
        {
            "id": "char-hei-ying",
            "name": "黑影",
            "role": "antagonist",
            "appearance": "全身笼罩在黑色斗篷中，只露出猩红色的双眼。身形高大，行动无声。",
            "personality": "冷酷无情，绝对服从组织的命令。",
            "background": "黑袍组织「星噬会」的低级追猎者，被派遣追踪逃走的星选者后裔。",
            "abilities": "暗影步——可在阴影中穿梭移动。",
            "speech_style": "沉默寡言，只在必要时开口，语气阴冷。",
        },
    ]


def _generate_world() -> list[dict]:
    return [
        {
            "id": "world-qingyun",
            "name": "青云镇",
            "category": "location",
            "description": "位于帝国南方边境的小镇，以铁矿和锻造闻名。镇后有一座无名小山，是镇民观星的好去处。",
            "notable_features": ["铁匠铺", "后山观星台", "镇口古槐树"],
        },
        {
            "id": "world-xingluo",
            "name": "星落城",
            "category": "location",
            "description": "北方大城，传说为星辰坠落之地。星选者的发源地，城中有一座古老的观星塔。",
            "notable_features": ["观星塔", "月华神殿", "地下密道"],
        },
        {
            "id": "world-chenxili",
            "name": "星辰之力",
            "category": "rule",
            "description": "宇宙星体散发的能量，少数天赋者可以感知和引导。分为日、月、星三种属性，分别对应不同的能力表现。",
            "notable_features": [
                "日之力：爆发、毁灭",
                "月之力：隐匿、幻术",
                "星之力：感知、引导",
            ],
        },
        {
            "id": "world-xingshihui",
            "name": "星噬会",
            "category": "faction",
            "description": "神秘组织，以猎杀星选者和收集星辰之力为目的。成员身穿黑袍，核心人员身份不明。",
            "notable_features": ["黑衣黑袍", "暗影步法", "遍布大陆的情报网"],
        },
        {
            "id": "world-xingxuanzhe",
            "name": "星选者",
            "category": "race",
            "description": "能够感知和操控星辰之力的人类。并非独立的种族，而是天赋异禀者的统称。历史上的星选者曾建立辉煌的星辰帝国。",
            "notable_features": ["天生感知星辰能量", "可觉醒日/月/星之力"],
        },
    ]


def _generate_summaries() -> list[dict]:
    return [
        {
            "section_id": "sec-1-1",
            "section_title": "第一节：流星雨",
            "summary": "林星在流星雨之夜于后山觉醒星辰之力。一颗流星坠落在他身边，触碰陨石时体内爆发出星光，他短暂地看到了奇异的星空幻象。",
            "key_events": [
                "林星独自上山观测流星雨",
                "一颗流星坠落在附近",
                "林星触碰陨石后觉醒星辰之力",
                "觉醒时看到星空幻象",
            ],
            "character_state_changes": {
                "char-lin-xing": "从普通少年变为觉醒星辰之力的星选者",
            },
            "world_setting_changes": {},
        }
    ]


def _write_json(filepath: Path, data):
    filepath.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
