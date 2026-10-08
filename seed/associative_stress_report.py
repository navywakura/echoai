"""Read completed CAP-STRESS-1 outputs and render measured capacity curves."""
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1] / 'lab/seed/associative-stress-20261002'


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary = json.loads((ROOT / 'summary.json').read_text())
    audit = json.loads((ROOT / 'audit.json').read_text())
    assert audit['valid'] is True
    rows = [r for f in sorted((ROOT / 'primary').glob('*.json'))
            for r in json.loads(f.read_text())['rows']]
    assert len(rows) == 200
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for ax, corrupt in zip(axes, (0, 2)):
        curve = [r for r in summary['curve'] if r['corrupt_features'] == corrupt]
        for bank, label, color in [('65536', '65.536 contadores', '#64748b'),
                                   ('500000', '500.000 contadores', '#7c3aed'),
                                   ('exact', 'Diccionario sin colisiones', '#15803d')]:
            x = [r['contexts'] for r in curve]
            y = [100*r['accuracy'][bank] for r in curve]
            ax.plot(x, y, marker='o', label=label, color=color,
                    linestyle='--' if bank == 'exact' else '-')
            if bank != 'exact':
                lo, hi = [], []
                for count in x:
                    values = [100*r['metrics'][bank]['accuracy'] for r in rows
                              if r['contexts'] == count and r['corrupt_features'] == corrupt]
                    lo.append(min(values)); hi.append(max(values))
                ax.fill_between(x, lo, hi, color=color, alpha=.10)
        ax.axhline(95, color='#a3a3a3', linewidth=.7)
        ax.set_xscale('log', base=2)
        ax.set_xticks(x, ['256', '1.024', '4.096', '16.384', '65.536'])
        ax.set_ylim(0, 104)
        ax.set_title('Sin corrupción' if corrupt == 0 else '25 % de rasgos sustituidos')
        ax.set_xlabel('Contextos ya almacenados')
        ax.grid(alpha=.15)
    axes[0].set_ylabel('Recuperación correcta (%)')
    axes[0].legend(loc='lower left', fontsize=8)
    fig.suptitle('ECHO · capacidad del banco asociativo', weight='bold')
    fig.text(.5, .01, '20 semillas · bandas: mínimo–máximo · recuperación sintética; no puntuación ARC',
             ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, .95))
    for ext in ('png', 'svg'):
        fig.savefig(ROOT / f'capacity-curves.{ext}', dpi=180)
    costs = {}
    for bank in ('65536', '500000'):
        last = [r for r in rows if r['contexts'] == 65536 and r['corrupt_features'] == 0]
        costs[bank] = {'mean_fit_cpu_seconds_all_loads': statistics.mean(r['fit_cpu_seconds'][bank] for r in last),
                       'query_cpu_seconds_all_seeds_conditions': sum(r['query_cpu_seconds'][bank] for r in rows),
                       'vector_bytes': int(bank)}
    out = {'primary': summary['primary'], 'audit': audit, 'costs': costs,
           'max_worker_rss_mib': max(r['rss_kib'] for r in rows)/1024,
           'queries_per_arm': sum(r['queries'] for r in rows),
           'saturated_255_any': any(b['saturated_255'] for r in rows for b in r['banks'].values())}
    (ROOT / 'report.json').write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
