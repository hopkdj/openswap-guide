#!/usr/bin/env python3
"""
自动化内容生成脚本
批量生成开源替代方案文章
"""
import os
import sys
import json

# 内容模板库
TEMPLATES = {
    "comparison": {
        "structure": [
            "title", "date", "tags", "draft", "description",
            "## Quick Comparison Table",
            "## 1. [Software A]",
            "## 2. [Software B]",
            "## 3. [Software C]",
            "## Feature Comparison",
            "## Performance Benchmarks",
            "## Frequently Asked Questions",
            "## Recommendation"
        ]
    },
    "guide": {
        "structure": [
            "title", "date", "tags", "draft", "description",
            "## Why [Topic]?",
            "## Prerequisites",
            "## Installation Steps",
            "## Configuration",
            "## Docker Deployment",
            "## Troubleshooting",
            "## Frequently Asked Questions",
            "## Next Steps"
        ]
    }
}

# 关键词矩阵
KEYWORDS = {
    "self-hosted": [
        "self hosted email server",
        "self hosted cloud storage",
        "self hosted password manager",
        "self hosted photo backup",
        "self hosted note taking",
        "self hosted calendar",
        "self hosted dns",
        "self hosted vpn server",
        "self hosted backup solution",
        "self hosted monitoring"
    ],
    "alternatives": [
        "slack alternative open source",
        "trello alternative self hosted",
        "notion alternative open source",
        "zoom alternative self hosted",
        "dropbox alternative open source",
        "spotify alternative self hosted",
        "obsidian alternative open source",
        "todoist alternative self hosted",
        "evernote alternative open source",
        "lastpass alternative self hosted"
    ],
    "docker": [
        "docker compose home server",
        "docker media server setup",
        "docker reverse proxy guide",
        "docker backup strategy",
        "docker monitoring stack",
        "docker ci cd pipeline",
        "docker database backup",
        "docker logging setup",
        "docker ssl automation",
        "docker swarm vs compose"
    ]
}

def generate_article_outline(topic, article_type="comparison"):
    """生成文章大纲"""
    template = TEMPLATES.get(article_type, TEMPLATES["comparison"])
    return template["structure"]

def generate_keywords_batch(category, count=5):
    """生成一批关键词"""
    keywords = KEYWORDS.get(category, [])
    return keywords[:count]

def batch_generate_topics():
    """批量生成待写文章列表"""
    topics = []
    
    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            article_type = "guide" if "how to" in keyword or "setup" in keyword else "comparison"
            topics.append({
                "keyword": keyword,
                "type": article_type,
                "status": "pending"
            })
    
    return topics

if __name__ == "__main__":
    print("📝 OpenSwap Guide - 内容生成管线")
    print("=" * 50)
    
    # 显示待生成文章
    topics = batch_generate_topics()
    print(f"\n待生成文章: {len(topics)} 篇")
    print("\n按类别:")
    for category in KEYWORDS:
        count = len(KEYWORDS[category])
        print(f"  {category}: {count} 篇")
    
    print("\n示例文章:")
    for topic in topics[:10]:
        print(f"  [{topic['type']}] {topic['keyword']}")
    
    print("\n✅ 内容管线已就绪")
    print("运行以下命令生成新文章:")
    print("  python generate_content.py --topic 'topic' --type 'comparison|guide'")
