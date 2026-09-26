"""Compare prepared grades to original source support, without authoring a scene.

An inward fit error is not evidence that the adjacent road should be moved.
This separates model extrapolation, source disagreement and absent evidence.
"""
import hashlib
import json
import numpy as np
from shapely.geometry import Point, shape
from scipy.interpolate import BSpline
from workspace_paths import read_path, write_path
from diagnose_bank_tram_platform import Layers


def main():
    paths = [read_path('derived/bellevue/bank_tram_shelter/' + n) for n in
             ['platform_input.json', 'complete_ground_support.json']]
    platform, support = [json.loads(p.read_text()) for p in paths]
    t = np.asarray([r['triangle'] for r in support['original_candidate_faces']])
    source = Layers([dict(name='immutable_source_ground', kind='retained_photo',
                         vertices_world=t.reshape(-1, 3),
                         faces=np.arange(t.size // 3).reshape(-1, 3))])
    profile = platform['report']['profile']
    start = np.asarray(profile['origin_xy'])
    basis = np.array([profile['along'], profile['across']]).T
    spline = BSpline(profile['knots'], profile['coefficients'], profile['degree'])
    poly = shape(platform['geometry_local'])
    comparisons = []
    for row in platform['report']['perimeter_road_comparison']:
        xy = np.asarray(row['xy'])
        u, v = (xy - start) @ basis
        hits = source.hits(xy)
        unique = sorted({round(h['z'], 5) for h in hits})
        ambiguous = bool(unique) and max(unique) - min(unique) > .06
        # Do not select the layer merely because it agrees with the model.
        z = float(np.median(unique)) if unique and not ambiguous else None
        comparisons.append(dict(**row, raw_profile_z=float(spline(u) + v * profile['crossfall']),
                                source_hits=hits, source_layer_ambiguous=ambiguous,
                                source_median_z=z,
                                prepared_minus_source_m=None if z is None else row['platform_z']-z,
                                old_road_minus_source_m=None if z is None else row['road_z']-z))
    negative = [r for r in comparisons if r['upstand_m'] < -.002]
    witnessed = [r for r in negative if r['source_median_z'] is not None]
    report = dict(
        inputs=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
        negative_count=len(negative), negative_with_unambiguous_source=len(witnessed),
        negative_without_source=sum(not r['source_hits'] for r in negative),
        negative_prepared_minus_source_quantiles_m=np.quantile(
            [r['prepared_minus_source_m'] for r in witnessed], [0, .1, .5, .9, 1]).tolist(),
        negative_old_road_minus_source_quantiles_m=np.quantile(
            [r['old_road_minus_source_m'] for r in witnessed], [0, .1, .5, .9, 1]).tolist(),
        perimeter=comparisons, current_native_road_verified=False, native_changed=False,
        conclusions=[
            'Before end-nose evidence was included, the unconstrained AV355-only spline produced a false low extension.',
            'Remaining negative upstands need both current-native road and source-boundary checks; they do not prove the old road is wrong.',
            'Near-horizontal photography at a cadastral edge can contain curb mixing. Agreement in centimetres is not survey accuracy.'
        ])
    write_path('derived/bellevue/bank_tram_shelter/grade_model_diagnosis.json').write_text(
        json.dumps(report, indent=2), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 8), layout='constrained')
    polygon = np.asarray(poly.exterior.coords)
    centres = t.mean(1)
    for ax in axes:
        ax.plot(*polygon.T, color='#202020', lw=.7)
        ax.set_aspect('equal')
        ax.set_xlabel('Local east [m]')
    p = axes[0].scatter(*centres[:, :2].T, c=centres[:, 2], s=11, cmap='viridis')
    fig.colorbar(p, ax=axes[0], shrink=.6, label='Original photo height [m]')
    axes[0].set_title('Original source ground candidates')
    q = np.array([[*r['xy'], r['upstand_m']] for r in comparisons])
    p = axes[1].scatter(*q[:, :2].T, c=q[:, 2], s=9, cmap='coolwarm', vmin=-.15, vmax=.15)
    fig.colorbar(p, ax=axes[1], shrink=.6, label='Prepared floor minus old road [m]')
    axes[1].set_title('Candidate edge: not yet constructed')
    q = np.array([[*r['xy'], r['prepared_minus_source_m']] for r in comparisons
                  if r['source_median_z'] is not None])
    p = axes[2].scatter(*q[:, :2].T, c=q[:, 2], s=9, cmap='coolwarm', vmin=-.15, vmax=.15)
    fig.colorbar(p, ax=axes[2], shrink=.6, label='Prepared floor minus source [m]')
    axes[2].set_title('Boundary witnesses; gaps stay unfilled')
    fig.suptitle('AV355 + AV456 + AV457 — source/model diagnosis only')
    fig.savefig(write_path('derived/bellevue/bank_tram_shelter/grade_model_diagnosis.png'), dpi=130)
    print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','perimeter']}, indent=2))


if __name__ == '__main__':
    main()
