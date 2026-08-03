"""Style board for traceability-aware building-code workflow figures.

Exports editable SVG, PDF, and review PNG using Python/matplotlib only.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams.update({'font.size': 7, 'pdf.fonttype': 42})

COLORS = {
    'ink': '#2C3440', 'muted': '#6B7280', 'line': '#AEB7C2',
    'input': '#DCEAF7', 'model': '#DCDCF0', 'review': '#F2E5C8',
    'graph': '#D9EEE7', 'decision': '#DCE9D6', 'reject': '#F5D8D6',
    'white': '#FFFFFF', 'wash': '#F8FAFC'
}


def box(ax, x, y, w, h, title, subtitle='', color='white', edge=None, radius=0.035, title_size=7):
    edge = edge or COLORS['line']
    patch = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.012,rounding_size={radius}",
                           linewidth=0.8, facecolor=COLORS[color], edgecolor=edge)
    ax.add_patch(patch)
    ax.text(x + w/2, y + h*0.62, title, ha='center', va='center', color=COLORS['ink'],
            fontsize=title_size, fontweight='bold', wrap=True)
    if subtitle:
        ax.text(x + w/2, y + h*0.30, subtitle, ha='center', va='center', color=COLORS['muted'],
                fontsize=5.6, wrap=True)
    return patch


def arrow(ax, start, end, color=None, style='-|>', rad=0.0, lw=1.0):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=9, linewidth=lw,
                                 color=color or COLORS['ink'], connectionstyle=f"arc3,rad={rad}"))


def panel_heading(ax, label, title, note):
    ax.text(0.00, 1.02, label, transform=ax.transAxes, fontsize=10, fontweight='bold', va='bottom')
    ax.text(0.07, 1.02, title, transform=ax.transAxes, fontsize=8, fontweight='bold', va='bottom', color=COLORS['ink'])
    ax.text(0.07, 0.965, note, transform=ax.transAxes, fontsize=5.5, va='bottom', color=COLORS['muted'])


def style_linear(ax):
    panel_heading(ax, 'A', 'Linear ribbon', 'Best for Fig. 1: a fast, high-level method overview')
    stages = [
        ('Code corpus', 'clauses + metadata', 'input'),
        ('LLM proposal', 'structured candidates', 'model'),
        ('Expert review', 'accept / revise / reject', 'review'),
        ('Reviewed graph', 'rules + provenance', 'graph'),
        ('Assessment', 'pass / fail / pending', 'decision'),
    ]
    xs = [0.02, 0.22, 0.42, 0.62, 0.82]
    for index, ((title, subtitle, color), x) in enumerate(zip(stages, xs)):
        box(ax, x, 0.40, 0.15, 0.23, title, subtitle, color)
        if index < len(stages)-1:
            arrow(ax, (x+0.15, 0.515), (xs[index+1]-0.012, 0.515))
    ax.text(0.50, 0.23, 'Evidence spans and review status travel with every assertion', ha='center', color=COLORS['muted'], fontsize=6)


def style_loop(ax):
    panel_heading(ax, 'B', 'Evidence loop', 'Best for Fig. 2: explain why the workflow is trustworthy')
    box(ax, 0.04, 0.42, 0.18, 0.20, 'Clause', 'authoritative source', 'input')
    box(ax, 0.30, 0.42, 0.18, 0.20, 'Candidate extraction', 'entity · relation · rule', 'model')
    box(ax, 0.57, 0.42, 0.18, 0.20, 'Evidence review', 'continuous source span', 'review')
    box(ax, 0.82, 0.42, 0.14, 0.20, 'Accepted rule', 'auditable', 'graph')
    arrow(ax, (0.22, 0.52), (0.287, 0.52))
    arrow(ax, (0.48, 0.52), (0.557, 0.52))
    arrow(ax, (0.75, 0.52), (0.807, 0.52))
    box(ax, 0.56, 0.12, 0.19, 0.13, 'Revise / reject', 'no graph write', 'reject', title_size=6.5)
    arrow(ax, (0.66, 0.42), (0.66, 0.26), color='#B55C59')
    arrow(ax, (0.56, 0.185), (0.39, 0.40), color='#B55C59', rad=0.28)
    ax.text(0.66, 0.325, 'unsupported or incomplete', ha='center', va='center', fontsize=5.2, color='#9A4A47')
    ax.text(0.50, 0.78, 'Claim: an LLM proposal becomes knowledge only after evidence review', ha='center', color=COLORS['ink'], fontsize=6.2, fontweight='bold')


def style_swimlane(ax):
    panel_heading(ax, 'C', 'Traceability swimlane', 'Best for Fig. 3: show data, AI, human, and decision responsibilities')
    lanes = [('DATA', 0.67, 'input'), ('AI', 0.48, 'model'), ('HUMAN', 0.29, 'review'), ('DECISION', 0.10, 'decision')]
    for name, y, color in lanes:
        ax.add_patch(FancyBboxPatch((0.01, y), 0.98, 0.14, boxstyle='round,pad=0.005,rounding_size=0.02',
                                    linewidth=0, facecolor=COLORS[color], alpha=0.55))
        ax.text(0.025, y+0.07, name, va='center', fontsize=5.3, fontweight='bold', color=COLORS['muted'])
    box(ax, 0.13, 0.70, 0.15, 0.08, 'Imported clause', '', 'white', title_size=6)
    box(ax, 0.37, 0.51, 0.16, 0.08, 'JSON candidate', '', 'white', title_size=6)
    box(ax, 0.61, 0.32, 0.17, 0.08, 'Reviewed rule', '', 'white', title_size=6)
    box(ax, 0.81, 0.13, 0.15, 0.08, 'Assessment trace', '', 'white', title_size=6)
    arrow(ax, (0.205, 0.70), (0.43, 0.59), rad=-0.08)
    arrow(ax, (0.45, 0.51), (0.685, 0.40), rad=-0.08)
    arrow(ax, (0.695, 0.32), (0.885, 0.21), rad=-0.08)
    arrow(ax, (0.62, 0.32), (0.47, 0.59), color='#B55C59', rad=0.22, lw=0.85)
    ax.text(0.52, 0.43, 'revision loop', color='#9A4A47', fontsize=5.1, rotation=28)
    ax.text(0.50, 0.015, 'Every hand-off retains source clause, evidence span, and review state.', ha='center', fontsize=5.8, color=COLORS['muted'])


def main():
    fig, axes = plt.subplots(3, 1, figsize=(7.20, 5.20))  # 183 mm wide
    fig.patch.set_facecolor('white')
    for ax, drawer in zip(axes, (style_linear, style_loop, style_swimlane)):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_axis_off()
        ax.set_facecolor(COLORS['wash'])
        drawer(ax)
    fig.subplots_adjust(left=0.035, right=0.985, top=0.95, bottom=0.045, hspace=0.36)
    out = Path(__file__).resolve().parent / 'outputs' / 'flowchart_style_board'
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out.with_suffix('.svg'), bbox_inches='tight')
    fig.savefig(out.with_suffix('.pdf'), bbox_inches='tight')
    fig.savefig(out.with_suffix('.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    from pathlib import Path
    main()
