#!/usr/bin/env python3
"""
PPT Harness Validation Script
Validates slide content against harness rules.

Checks:
1. text_length: bullet count, bullet char count, title char count
2. format_compliance: required fields presence
3. duplication: 2-gram Jaccard similarity between slides
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter


def load_harness(harness_path):
    """Load harness rules from JSON file."""
    with open(harness_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def count_korean_chars(text):
    """Count Korean characters (ignoring whitespace)."""
    return len(text.strip())


def count_bullets(key_points):
    """Count bullet points."""
    return len(key_points) if key_points else 0


def check_text_length(slides, rules):
    """
    Check text length constraints.
    Returns: (passed, violations list)
    """
    max_bullets = rules.get('rules', {}).get('text_constraints', {}).get('max_bullets_per_slide', 3)
    max_chars_bullet = rules.get('rules', {}).get('text_constraints', {}).get('max_chars_per_bullet', 20)
    max_title_len = rules.get('rules', {}).get('text_constraints', {}).get('max_title_length', 30)

    violations = []

    for slide in slides:
        slide_num = slide.get('slide_number', '?')
        title = slide.get('title', '')
        key_points = slide.get('key_points', [])

        # Check title length
        title_len = count_korean_chars(title)
        if title_len > max_title_len:
            violations.append({
                'slide': slide_num,
                'field': 'title',
                'actual': title_len,
                'limit': max_title_len,
                'message': f'Title exceeds {max_title_len} chars'
            })

        # Check bullet count
        bullet_count = count_bullets(key_points)
        if bullet_count > max_bullets:
            violations.append({
                'slide': slide_num,
                'field': 'bullets',
                'actual': bullet_count,
                'limit': max_bullets,
                'message': f'Exceeds {max_bullets} bullets'
            })

        # Check each bullet length
        for i, point in enumerate(key_points, 1):
            bullet_len = count_korean_chars(point)
            if bullet_len > max_chars_bullet:
                violations.append({
                    'slide': slide_num,
                    'field': f'bullets[{i}]',
                    'actual': bullet_len,
                    'limit': max_chars_bullet,
                    'message': f'Bullet {i} exceeds {max_chars_bullet} chars'
                })

    return len(violations) == 0, violations


def check_format_compliance(slides, rules):
    """
    Check if all required fields are present.
    Returns: (passed, violations list)
    """
    required_fields = rules.get('rules', {}).get('output_format', {}).get('required_fields', [])

    violations = []

    for slide in slides:
        slide_num = slide.get('slide_number', '?')
        missing_fields = []

        for field in required_fields:
            if field not in slide or slide[field] is None:
                missing_fields.append(field)

        if missing_fields:
            violations.append({
                'slide': slide_num,
                'field': 'required_fields',
                'missing': missing_fields,
                'message': f'Missing fields: {", ".join(missing_fields)}'
            })

    return len(violations) == 0, violations


def get_2grams(text):
    """Extract 2-grams from text (split by whitespace/punctuation)."""
    # Normalize text: lowercase, remove punctuation
    import re
    normalized = re.sub(r'[^\w\s]', '', text.lower())
    words = normalized.split()

    grams = set()
    for i in range(len(words) - 1):
        grams.add(tuple(sorted([words[i], words[i+1]]))

    return grams


def jaccard_similarity(set1, set2):
    """Calculate Jaccard similarity between two sets."""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


def check_duplication(slides, threshold=0.4):
    """
    Check for text duplication between slides using 2-gram Jaccard similarity.
    Returns: (passed, violations list)
    """
    violations = []

    # Combine title + bullets for each slide into text
    slide_texts = []
    for slide in slides:
        slide_num = slide.get('slide_number', '?')
        title = slide.get('title', '')
        key_points = slide.get('key_points', [])
        text = title + ' ' + ' '.join(key_points)
        grams = get_2grams(text)
        slide_texts.append((slide_num, grams))

    # Compare each slide with previous ones
    for i in range(len(slide_texts)):
        curr_num, curr_grams = slide_texts[i]

        for j in range(i):
            prev_num, prev_grams = slide_texts[j]
            similarity = jaccard_similarity(curr_grams, prev_grams)

            if similarity >= threshold:
                violations.append({
                    'slide': curr_num,
                    'related_slide': prev_num,
                    'similarity': f'{similarity:.2f}',
                    'threshold': f'{threshold:.2f}',
                    'message': f'Too similar to slide {prev_num}'
                })
                break  # Only report first duplicate per slide

    return len(violations) == 0, violations


def main():
    parser = argparse.ArgumentParser(description='PPT Harness Validation Script')
    parser.add_argument('--slides', required=True, help='Path to slides JSON file')
    parser.add_argument('--harness', required=True, help='Path to harness JSON file')
    parser.add_argument('--checks', default='all', help='Comma-separated checks to run (default: all)')
    parser.add_argument('--output', choices=['json', 'text'], default='json', help='Output format')

    args = parser.parse_args()

    # Load inputs
    slides_path = Path(args.slides)
    harness_path = Path(args.harness)

    try:
        with open(slides_path, 'r', encoding='utf-8') as f:
            slides = json.load(f)
    except Exception as e:
        result = {
            'passed': False,
            'error': f'Failed to load slides: {e}'
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        harness = load_harness(harness_path)
    except Exception as e:
        result = {
            'passed': False,
            'error': f'Failed to load harness: {e}'
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Parse checks
    requested_checks = [c.strip() for c in args.checks.lower().split(',')] if args.checks != 'all' else [
        'text_length', 'format_compliance', 'duplication'
    ]

    # Run checks
    checks = {}

    if 'text_length' in requested_checks or 'all' in requested_checks:
        passed, violations = check_text_length(slides, harness)
        checks['text_length'] = {
            'passed': passed,
            'violations': violations
        }

    if 'format_compliance' in requested_checks or 'all' in requested_checks:
        passed, violations = check_format_compliance(slides, harness)
        checks['format_compliance'] = {
            'passed': passed,
            'violations': violations
        }

    if 'duplication' in requested_checks or 'all' in requested_checks:
        passed, violations = check_duplication(slides)
        checks['duplication'] = {
            'passed': passed,
            'violations': violations
        }

    # Overall result
    all_passed = all(check.get('passed', False) for check in checks.values())

    # Count total violations
    total_violations = sum(len(check.get('violations', [])) for check in checks.values())
    passed_count = sum(1 for check in checks.values() if check.get('passed', False))
    total_checks = len(checks)

    result = {
        'passed': all_passed,
        'summary': f'{passed_count}/{total_checks} checks passed',
        'total_violations': total_violations,
        'checks': checks
    }

    if args.output == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Text output
        print(f"{'✅' if all_passed else '❌'} Validation Result")
        print(f"Summary: {result['summary']}")
        if total_violations > 0:
            print(f"\nTotal Violations: {total_violations}\n")
            for check_name, check_result in checks.items():
                violations = check_result.get('violations', [])
                if violations:
                    print(f"\n[{check_name.upper()}]")
                    for v in violations:
                        print(f"  Slide {v.get('slide')}: {v.get('message')}")
        else:
            print("\n✅ All checks passed!")


if __name__ == '__main__':
    main()
