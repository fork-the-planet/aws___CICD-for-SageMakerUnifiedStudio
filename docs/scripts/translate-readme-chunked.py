#!/usr/bin/env python3
"""
Translate README.md in chunks to handle large files.
Splits by major sections (##) and translates each independently.
"""

import boto3
import json
import re
import sys
from pathlib import Path
from typing import List, Tuple

LANGUAGES = {
    'fr': 'French',
    'he': 'Hebrew',
    'it': 'Italian',
    'ja': 'Japanese',
    'pt': 'Portuguese',
    'zh': 'Chinese (Simplified)',
}

def split_into_sections(content: str) -> List[Tuple[str, str]]:
    """Split markdown by ## headers, keeping structure."""
    sections = []
    current_section = []
    current_header = "header"
    
    lines = content.split('\n')
    for line in lines:
        if line.startswith('## '):
            # Save previous section
            if current_section:
                sections.append((current_header, '\n'.join(current_section)))
            # Start new section
            current_header = line
            current_section = [line]
        else:
            current_section.append(line)
    
    # Add last section
    if current_section:
        sections.append((current_header, '\n'.join(current_section)))
    
    return sections

def translate_chunk(content: str, language: str, lang_code: str) -> str:
    """Translate a chunk using Bedrock."""
    bedrock = boto3.client('bedrock-runtime')
    
    rtl_note = ""
    if lang_code == 'he':
        rtl_note = "\n- For Hebrew: Wrap entire document in <div dir=\"rtl\">...</div>"
    
    prompt = f"""Translate the following markdown content to {language}. Output ONLY the translated markdown, no explanations.

CRITICAL RULES:
- Translate all natural language text (headings, descriptions, explanations) into {language}
- Keep the following UNCHANGED (do not translate): code blocks, inline code, commands, file names, file paths, URLs, AWS service names, CLI command names, YAML keys
- Keep these technical terms in English but translate the surrounding sentence: CLI, CI/CD, DevOps, API, SDK, DAG, ML, GenAI, IAM, IdC, VPC
- Brand names stay in English: AWS, Amazon, SageMaker, Bedrock, QuickSight, Glue, Airflow, GitHub, Python
- Translate descriptive text naturally — do NOT keep sentences in English just because they contain technical terms
- Preserve ALL markdown formatting exactly (headers, bold, links, badges, lists, tables){rtl_note}

{content}"""
    
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    
    try:
        response = bedrock.invoke_model(
            modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
            body=json.dumps(request_body)
        )
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text'].strip()
    except Exception as e:
        print(f"  Error: {e}")
        return content  # Return original on error

def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    readme_path = project_root / "README.md"
    
    print(f"Reading {readme_path}...")
    with open(readme_path, 'r', encoding='utf-8') as f:
        source_content = f.read()

    # Strip the language badge panel from source — the translation script
    # adds its own badge panel with correct relative paths and highlighting
    source_lines = source_content.split('\n')
    source_lines = [
        line for line in source_lines
        if not re.match(r'\[!\[(?:en|pt|fr|it|ja|zh|he)\]', line)
    ]
    source_content = '\n'.join(source_lines)

    print(f"Source: {len(source_content)} chars, {len(source_content.splitlines())} lines\n")
    
    # Split into sections
    sections = split_into_sections(source_content)
    print(f"Split into {len(sections)} sections\n")
    
    for lang_code, lang_name in LANGUAGES.items():
        print(f"Translating to {lang_name} ({lang_code})...")
        translated_sections = []
        
        for i, (header, section_content) in enumerate(sections, 1):
            print(f"  Section {i}/{len(sections)}: {header[:50]}...")
            translated = translate_chunk(section_content, lang_name, lang_code)
            translated_sections.append(translated)
        
        # Combine sections
        full_translation = '\n\n'.join(translated_sections)
        
        # Add language badges at the top
        badges = [
            "[![en](https://img.shields.io/badge/lang-en-gray.svg)](../../../README.md)",
            "[![pt](https://img.shields.io/badge/lang-pt-gray.svg)](../pt/README.md)",
            "[![fr](https://img.shields.io/badge/lang-fr-gray.svg)](../fr/README.md)",
            "[![it](https://img.shields.io/badge/lang-it-gray.svg)](../it/README.md)",
            "[![ja](https://img.shields.io/badge/lang-ja-gray.svg)](../ja/README.md)",
            "[![zh](https://img.shields.io/badge/lang-zh-gray.svg)](../zh/README.md)",
            "[![he](https://img.shields.io/badge/lang-he-gray.svg)](../he/README.md)"
        ]
        
        # Highlight current language
        badge_map = {'pt': 1, 'fr': 2, 'it': 3, 'ja': 4, 'zh': 5, 'he': 6}
        if lang_code in badge_map:
            idx = badge_map[lang_code]
            badges[idx] = badges[idx].replace('-gray.svg)', '-brightgreen.svg?style=for-the-badge)')

        badge_bar = '\n'.join(badges)
        back_link = '\n\n← [Back to Main README](../../../README.md)'

        # Wrap Hebrew in RTL div and fix code blocks
        if lang_code == 'he':
            # Wrap code blocks in LTR divs
            pattern = r'(```[\s\S]*?```)'
            full_translation = re.sub(pattern, r'<div dir="ltr">\n\n\1\n\n</div>', full_translation)
            full_translation = f'<div dir="rtl">\n\n{badge_bar}{back_link}\n\n{full_translation}\n\n</div>'
        else:
            full_translation = f'{badge_bar}{back_link}\n\n{full_translation}'
        
        # Save
        output_dir = project_root / "docs" / "langs" / lang_code
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "README.md"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_translation)
        
        print(f"✅ Saved: {len(full_translation)} chars, {len(full_translation.splitlines())} lines\n")

if __name__ == "__main__":
    main()
