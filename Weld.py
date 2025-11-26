import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# Page config + CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="Fillet Weld Capacity – Calc Sheet",
    layout="wide"
)

st.markdown(
    """
    <style>
    /* General page look */
    .main {
        background-color: #f5f5f5;
        padding-top: 10px;
    }

    /* Header bar */
    .report-header {
        background-color: #1f4e79;
        color: white;
        padding: 0.4rem 1.2rem;
        display: flex;
        justify-content: space-between;
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .report-header span {
        margin-right: 1.2rem;
    }

    /* Card / sheet block */
    .sheet-box {
        background-color: white;
        padding: 0.9rem 1.3rem;
        border-radius: 4px;
        border: 1px solid #d0d0d0;
        margin-bottom: 0.8rem;
    }

    .section-title {
        font-size: 1.0rem;
        font-weight: 700;
        border-bottom: 2px solid #d0d0d0;
        margin-bottom: 0.5rem;
        padding-bottom: 0.15rem;
    }

    .small-caption {
        font-size: 0.8rem;
        color: #555;
    }

    /* Make all numeric inputs look like yellow Excel cells */
    div[data-baseweb="input"] input {
        background-color: #fffad1 !important;
    }

    /* Tables for summary / checks */
    table.calc-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 0.2rem;
        font-size: 0.9rem;
    }
    table.calc-table th,
    table.calc-table td {
        border: 1px solid #bdbdbd;
        padding: 4px 6px;
        text-align: left;
    }
    table.calc-table th {
        background-color: #e0e0e0;
        font-weight: 700;
    }
    .ok-cell {
        background-color: #e8f5e9;
        color: #1b5e20;
        font-weight: 700;
        text-align: center;
    }
    .ng-cell {
        background-color: #ffebee;
        color: #b71c1c;
        font-weight: 700;
        text-align: center;
    }

    /* Printing */
    @media print {
        .main {
            background: white;
        }
        .sheet-box {
            break-inside: avoid;
            page-break-inside: avoid;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Header bar
# ---------------------------------------------------------
st.markdown(
    """
    <div class="report-header">
        <div>
            <span>REFERENCES</span>
            <span>CALCULATIONS</span>
            <span>RESULTS</span>
        </div>
        <div>Fillet Weld Capacity – AISC 360-16 (J2.4)</div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Calculation sheet header (project info)
# ---------------------------------------------------------
st.markdown('<div class="sheet-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Calculation Sheet Header</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
project = c1.text_input("Project", value="New Project")
client = c2.text_input("Client", value="")
calc_title = c3.text_input("Calculation Title", value="Fillet Weld in Shear")
engineer = c4.text_input("Engineer", value="Abdulrahman Salah")

c5, c6 = st.columns(2)
calc_id = c5.text_input("Calc ID / Ref", value="WELD-001")
calc_date = c6.date_input("Date")

st.markdown('</div>', unsafe_allow_html=True)

st.title("Fillet Weld Capacity – Calculation Sheet")

# ---------------------------------------------------------
# INPUTS SECTION (within sheet, yellow inputs)
# ---------------------------------------------------------
st.markdown('<div class="sheet-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Input Data</div>', unsafe_allow_html=True)

colL, colR = st.columns([2, 1])

with colL:
    c1, c2, c3 = st.columns(3)
    with c1:
        design_method = st.radio(
            "Design method",
            ["LRFD", "ASD"],
            index=0,
            help="LRFD uses φRₙ, ASD uses Rₙ/Ω."
        )
        F_exx = st.number_input(
            "Electrode strength F_EXX (ksi)",
            min_value=10.0,
            max_value=120.0,
            value=70.0,
            step=5.0
        )

    with c2:
        weld_size = st.number_input(
            "Fillet weld size w (in)",
            min_value=0.0625,
            max_value=1.0,
            value=0.25,
            step=0.0625,
            format="%.4f"
        )
        weld_length = st.number_input(
            "Length of one weld line L (in)",
            min_value=0.5,
            max_value=200.0,
            value=10.0,
            step=0.5
        )

    with c3:
        n_lines = st.number_input(
            "Number of weld lines n",
            min_value=1,
            max_value=20,
            value=2,
            step=1
        )
        Ru = st.number_input(
            "Applied shear on weld group R_u (kips)",
            min_value=0.0,
            max_value=5000.0,
            value=50.0,
            step=5.0
        )

with colR:
    st.markdown(
        """
        <div class="small-caption">
        <b>Specification Notes</b><br>
        – AISC 360-16, Ch. J – Welds<br>
        – Fillet weld in shear (J2.4)<br>
        – Effective throat: t = 0.707 w<br>
        – Nominal weld strength: 0.6 F<sub>EXX</sub> t
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# CALCULATIONS
# ---------------------------------------------------------
# Effective throat
t = 0.707 * weld_size  # in

# Nominal weld strength factor
Fw = 0.6 * F_exx  # ksi

# per-unit-length strength (kips/in)
rn_per_length = Fw * t

# total length
L_total = n_lines * weld_length  # in

# nominal group strength
Rn = rn_per_length * L_total  # kips

phi = 0.75
Omega = 2.0

if design_method == "LRFD":
    R_design = phi * Rn
    design_label = "φRₙ"
else:
    R_design = Rn / Omega
    design_label = "Rₙ / Ω"

utilization = Ru / R_design if R_design > 0 else 0.0
ok_global = utilization <= 1.0

# ---------------------------------------------------------
# INPUT SUMMARY TABLE
# ---------------------------------------------------------
st.markdown('<div class="sheet-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Input Summary</div>', unsafe_allow_html=True)

input_rows = [
    ("Design Method", design_method),
    ("F_EXX (ksi)", f"{F_exx:.1f}"),
    ("Weld size w (in)", f"{weld_size:.3f}"),
    ("Length of one weld line L (in)", f"{weld_length:.2f}"),
    ("Number of weld lines n", f"{n_lines:d}"),
    ("Total weld length L_total (in)", f"{L_total:.2f}"),
    ("Applied shear R_u (kips)", f"{Ru:.2f}")
]
df_inputs = pd.DataFrame(input_rows, columns=["Item", "Value"])
st.table(df_inputs)

st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# RESULT SUMMARY
# ---------------------------------------------------------
st.markdown('<div class="sheet-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Result Summary</div>', unsafe_allow_html=True)

result_rows = [
    ("Effective throat t (in)", f"{t:.3f}"),
    ("Nominal strength per unit length r_n (kips/in)", f"{rn_per_length:.2f}"),
    ("Total nominal strength R_n (kips)", f"{Rn:.2f}"),
    (f"Design strength {design_label} (kips)", f"{R_design:.2f}"),
    ("Demand / Capacity ratio R_u / Design Strength", f"{utilization:.2f}")
]
df_results = pd.DataFrame(result_rows, columns=["Result", "Value"])
st.table(df_results)

if ok_global:
    st.success("GLOBAL CHECK: OK – Demand is ≤ design strength.")
else:
    st.error("GLOBAL CHECK: NG – Demand exceeds design strength.")

st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# DETAILED CALCULATIONS (with LaTeX)
# ---------------------------------------------------------
st.markdown('<div class="sheet-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Detailed Calculations</div>', unsafe_allow_html=True)

st.markdown("**1. Effective throat thickness**  (AISC 360-16 J2.4)", unsafe_allow_html=True)
st.latex(r"t = 0.707\,w")
st.latex(rf"t = 0.707 \times {weld_size:.3f}\,\text{{in}} = {t:.3f}\,\text{{in}}")

st.markdown("**2. Nominal weld strength per unit length**  (AISC 360-16 J2.4)", unsafe_allow_html=True)
st.latex(r"F_w = 0.6\,F_{EXX}")
st.latex(rf"F_w = 0.6 \times {F_exx:.1f}\,\text{{ksi}} = {Fw:.1f}\,\text{{ksi}}")

st.latex(r"r_n = F_w\,t = 0.6\,F_{EXX}\,t")
st.latex(
    rf"r_n = {Fw:.1f}\,\text{{ksi}} \times {t:.3f}\,\text{{in}}"
    rf" = {rn_per_length:.2f}\,\text{{kips/in}}"
)

st.markdown("**3. Total nominal strength of weld group**", unsafe_allow_html=True)
st.latex(r"L_{\text{total}} = n\,L")
st.latex(
    rf"L_{{\text{{total}}}} = {n_lines:d} \times {weld_length:.2f}\,\text{{in}}"
    rf" = {L_total:.2f}\,\text{{in}}"
)

st.latex(r"R_n = r_n\,L_{\text{total}}")
st.latex(
    rf"R_n = {rn_per_length:.2f}\,\text{{kips/in}} \times {L_total:.2f}\,\text{{in}}"
    rf" = {Rn:.2f}\,\text{{kips}}"
)

if design_method == "LRFD":
    st.markdown("**4. LRFD design strength and check**  (AISC 360-16 LRFD)", unsafe_allow_html=True)
    st.latex(r"\phi = 0.75")
    st.latex(r"\phi R_n = 0.75\,R_n")
    st.latex(
        rf"\phi R_n = 0.75 \times {Rn:.2f}\,\text{{kips}}"
        rf" = {R_design:.2f}\,\text{{kips}}"
    )
    st.latex(
        rf"\text{{Interaction ratio}} = \dfrac{{R_u}}{{\phi R_n}}"
        rf" = \dfrac{{{Ru:.2f}}}{{{R_design:.2f}}}"
        rf" = {utilization:.2f}"
    )
else:
    st.markdown("**4. ASD allowable strength and check**  (AISC 360-16 ASD)", unsafe_allow_html=True)
    st.latex(r"\Omega = 2.0")
    st.latex(r"R_{\text{allow}} = \dfrac{R_n}{\Omega}")
    st.latex(
        rf"R_{{\text{{allow}}}} = \dfrac{{{Rn:.2f}\,\text{{kips}}}}{{2.0}}"
        rf" = {R_design:.2f}\,\text{{kips}}"
    )
    st.latex(
        rf"\text{{Interaction ratio}} = \dfrac{{R_u}}{{R_{{\text{{allow}}}}}}"
        rf" = \dfrac{{{Ru:.2f}}}{{{R_design:.2f}}}"
        rf" = {utilization:.2f}"
    )

st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# DESIGN CHECK TABLE (clause column + OK/NG)
# ---------------------------------------------------------
st.markdown('<div class="sheet-box">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Design Checks (Clause – Check – Status)</div>', unsafe_allow_html=True)

if design_method == "LRFD":
    check_expr = f"R_u = {Ru:.2f} kips ≤ φR_n = {R_design:.2f} kips"
else:
    check_expr = f"R_u = {Ru:.2f} kips ≤ R_n / Ω = {R_design:.2f} kips"

status_class = "ok-cell" if ok_global else "ng-cell"
status_text = "OK" if ok_global else "NG"

check_table_html = f"""
<table class="calc-table">
    <tr>
        <th style="width:18%;">Clause</th>
        <th>Check</th>
        <th style="width:12%;">Status</th>
    </tr>
    <tr>
        <td>AISC 360-16 J2.4</td>
        <td>{check_expr}</td>
        <td class="{status_class}">{status_text}</td>
    </tr>
</table>
"""

st.markdown(check_table_html, unsafe_allow_html=True)

st.markdown(
    """
<div class="small-caption">
Notes:<br>
– Global check corresponds to weld group shear capacity.<br>
– Additional checks (minimum weld size, combined stresses, seismic provisions) should be added as required.<br>
– Print this sheet from the browser (Ctrl+P); layout is optimized for multi-page printing.
</div>
""",
    unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)
