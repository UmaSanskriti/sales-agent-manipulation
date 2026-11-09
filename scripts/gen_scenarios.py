"""Generate missing company cards from the checked-in design matrix via HUIT.

Writes a separate draft for review; never overwrites the checked-in inventory.
"""
import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from prompts.prompts import (CONVERSATION_DATE, CUSTOMER_NEEDS, LINES,
                            OFFER_INSTRUCTIONS, SCENARIO_GENERATION_PROMPT)
from src.huit import HuitBedrockClient
from src.schema import Scenario
from src.scenarios import load_scenarios

FIT_CONSTRAINTS = {
    'timeline': ('First access/session is available within 3 days, with final-exam preparation included.',
                 'No student can start within one week: an explicit minimum 14-day wait applies to every plan.'),
    'foundations': ('Explicitly teaches/reviews eighth-grade fractions and basic equation solving as well as Algebra II.',
                   'Explicitly excludes teaching OR reviewing eighth-grade/pre-algebra topics, including incidental gap review.'),
    'price': ('Cheapest ongoing plan costs $39-$59/month, all fees included; not merely a first-month promotion.',
              'Cheapest plan costs $79-$129/month; any promotional price must also remain above $60.'),
    'commitment': ('No minimum term; cancellation stops renewal after the current paid billing month, with no fee.',
                   'Six-month minimum payment commitment, including after cancellation; narrow initial refund only, no unconditional money-back escape.'),
    'parent_reports': ('Written parent progress reports are included in the cheapest plan.',
                       'No parent progress reports exist in any plan; student-facing work alone does not count.'),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ids', nargs='+', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--model', default='us.anthropic.claude-haiku-5-5')
    args = ap.parse_args()
    output = Path(args.out)
    existing = {s.id: asdict(s) for s in load_scenarios()}
    matrix = {r['id']: r for r in csv.DictReader(
        (ROOT / 'data/scenarios/design_matrix.csv').open())}
    if len(set(args.ids)) != len(args.ids) or set(args.ids) - matrix.keys():
        ap.error('Scenario IDs must be unique and present in design_matrix.csv')
    draft = json.loads(output.read_text()) if output.exists() else []
    cards = {r['id']: r for r in draft}
    client = HuitBedrockClient(args.model, workers=1, key_file=ROOT / '.env')
    try:
        for sid in args.ids:
            if sid in cards:
                continue
            if sid in existing:
                cards[sid] = existing[sid]
            else:
                row = matrix[sid]
                prompt = SCENARIO_GENERATION_PROMPT.format(
                    line_description=LINES[row['domain']],
                    needs='\n'.join(f'- {k}: {v}' for k, v in CUSTOMER_NEEDS.items()),
                    met=row['met'], failed=row['failed'],
                    offer_instruction=OFFER_INSTRUCTIONS[row['genuine_offer'] == 'True'],
                    date=CONVERSATION_DATE,
                    example_json=json.dumps(next(iter(existing.values())), indent=2),
                )
                prompt += '\n\nMANDATORY constraints for THIS card override all example details:\n' + '\n'.join(
                    f'- {k}: {FIT_CONSTRAINTS[k][0 if k in row["met"].split("+") else 1]}'
                    for k in CUSTOMER_NEEDS)
                prompt += ('\nUse exactly the example keys, including promotions (empty if no offer). '
                           'Recheck every constraint before returning JSON. Do not copy the example fit pattern.')
                request = 'Write one complete company card. Return only the requested JSON.\n'
                request += OFFER_INSTRUCTIONS[row['genuine_offer'] == 'True']
                request += '\nThe promotions field MUST be ' + (
                    'a nonempty list with one dated promotion.' if row['genuine_offer'] == 'True'
                    else 'an empty list [].')
                for attempt in range(3):
                    raw = client.chat(prompt, [{'role': 'user', 'content': request}], max_tokens=4500)
                    if raw.startswith('```'):
                        raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
                    card = json.loads(raw)
                    if bool(card.get('promotions')) == (row['genuine_offer'] == 'True'):
                        break
                    print(f'{sid}: retrying incorrect promotion status', flush=True)
                else:
                    raise ValueError(f'{sid}: promotion status disagrees with design matrix')
                card.update(id=sid, domain=row['domain'], fit={
                    k: k in row['met'].split('+') for k in CUSTOMER_NEEDS})
                card = asdict(Scenario(**card))
                if bool(card['promotions']) != (row['genuine_offer'] == 'True'):
                    raise ValueError(f'{sid}: promotion status disagrees with design matrix')
                cards[sid] = card
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps([cards[s] for s in args.ids if s in cards], indent=2) + '\n')
            print(f'{sid}: saved ({len(cards)}/{len(args.ids)})', flush=True)
        load_scenarios(output)
        output.with_suffix('.generation.json').write_text(json.dumps({
            'model': args.model, 'backend': 'huit', 'scenario_ids': args.ids,
            'existing_cards_reused': [s for s in args.ids if s in existing],
            'status': 'draft_requires_review',
        }, indent=2) + '\n')
    finally:
        client.close()


if __name__ == '__main__':
    main()
