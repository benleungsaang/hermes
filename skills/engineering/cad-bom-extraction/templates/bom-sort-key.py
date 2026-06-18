"""
BOM row sort key + cabinet-last rule.
B 2026-06-17 hard rule: Electrical cabinet always sorts last, regardless of count.
"""

def sort_key(g):
    """
    Sort BOM rows. Cabinet always last; otherwise descending by count, then name.
    """
    name = g.get('canonical_name', '') or g.get('rep_name', '')
    is_cabinet = 'cabinet' in name.lower() or '电箱' in name
    return (1 if is_cabinet else 0, -g.get('count', 0), name)


# Examples
if __name__ == '__main__':
    rows = [
        {'canonical_name': 'Transition conveyor', 'count': 4},
        {'canonical_name': 'Electrical cabinet', 'count': 2},
        {'canonical_name': 'Feeding conveyor', 'count': 1},
        {'canonical_name': 'Turnable unit', 'count': 1},
        {'canonical_name': 'HP-FB-370L', 'count': 1},
    ]
    rows.sort(key=sort_key)
    for r in rows:
        marker = '  ← cabinet (always last)' if 'cabinet' in r['canonical_name'].lower() else ''
        print(f"  ×{r['count']}  {r['canonical_name']}{marker}")
