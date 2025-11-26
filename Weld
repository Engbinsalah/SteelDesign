import streamlit as st

# ---------------------------------------------------------
# Page config
# ---------------------------------------------------------
st.set_page_config(
    page_title="Fillet Weld Capacity (AISC-style)",
    layout="centered"
)

st.title("Fillet Weld Capacity Calculator")
st.caption("Fillet weld in shear based on AISC-style equations (US customary units).")

st.markdown(
    """
This tool computes the design strength of a fillet weld group in shear.
It uses the classic relations:

- Effective throat:  $t = 0.707\,w$
- Nominal strength per unit length:  $r_n = 0.6\,F_{EXX}\,t$
- Total nominal strength:  $R_n = r_n\,L_{\\text{total}}$

Assumptions:
- Weld loaded in shear
- EXX electrodes (e.g., E70XX)
- US customary units (in, ksi, kips)
"""
)

# ---------------------------------------------------------
# Input section
# ---------------------------------------------------------
st.header("Input Data")

col1, col2 = st.columns(2)

with col1:
    design_method = st.radio(
        "Design method",
        ["LRFD", "ASD"],
        index=0,
        help="LRFD uses φRn, ASD uses Rn/Ω."
    )

    F_exx = st.number_input(
        "Electrode strength $F_{EXX}$ (ksi)",
        min_value=10.0,
        max_value=120.0,
        value=70.0,
        step=5.0,
        help="Typical: 70 ksi for E70XX electrodes."
    )

    weld_size = st.number_input(
        "Fillet weld size $w$ (in)",
        min_value=0.0625,
        max_value=1.0,
        value=0.25,
        step=0.0625,
        format="%.4f",
        help="Leg size of the fillet weld."
    )

with col2:
    weld_length = st.number_input(
        "Length of one weld line $L$ (in)",
        min_value=0.5,
        max_value=200.0,
        value=10.0,
        step=0.5,
        help="Clear length of a single weld line."
    )

    n_lines = st.number_input(
        "Number of identical weld lines $n$",
        min_value=1,
        max_value=20,
        value=2,
        step=1,
        help="Number of lines with same size and length."
    )

    Ru = st.number_input(
        "Applied shear on weld group $R_u$ (kips)",
        min_value=0.0,
        max_value=5000.0,
        value=50.0,
        step=5.0,
        help="Factored load for LRFD or service-level load for ASD."
    )

st.markdown("---")

# ---------------------------------------------------------
# Calculations
# ---------------------------------------------------------
# Effective throat
t = 0.707 * weld_size  # in

# Nominal weld strength per unit area factor
Fw = 0.6 * F_exx  # ksi

# Nominal strength per unit length (kips/in)
# Fw [kips/in^2] * t [in] = r_n [kips/in]
rn_per_length = Fw * t

# Total length of weld group
L_total = n_lines * weld_length  # in

# Nominal strength of weld group
Rn = rn_per_length * L_total  # kips

phi = 0.75
Omega = 2.0

if design_method == "LRFD":
    R_design = phi * Rn
    capacity_label = r"$\phi R_n$"
    phi_or_Omega = phi
else:
    R_design = Rn / Omega
    capacity_label = r"$R_n / \Omega$"
    phi_or_Omega = Omega

# Utilization ratio
utilization = Ru / R_design if R_design > 0 else 0.0

# ---------------------------------------------------------
# Summary output
# ---------------------------------------------------------
st.header("Capacity Summary")

colA, colB = st.columns(2)

with colA:
    st.metric(label="Total nominal strength $R_n$ (kips)", value=f"{Rn:.2f}")
with colB:
    st.metric(label=f"Design strength {capacity_label} (kips)", value=f"{R_design:.2f}")

st.metric(
    label="Demand / Capacity ratio",
    value=f"{utilization:.2f}",
)

if utilization <= 1.0:
    st.success("OK: Demand is less than or equal to design strength.")
else:
    st.error("NG: Demand exceeds design strength.")

st.markdown("---")

# ---------------------------------------------------------
# Detailed calculation report
# ---------------------------------------------------------
st.header("Step-by-Step Calculation Report")

st.subheader("1. Input Data")

st.markdown(
    f"""
- Design method: **{design_method}**
- Electrode strength:  $F_{{EXX}} = {F_exx:.1f}\\,\\text{{ksi}}$
- Fillet weld size:  $w = {weld_size:.3f}\\,\\text{{in}}$
- Length of one weld line:  $L = {weld_length:.2f}\\,\\text{{in}}$
- Number of weld lines:  $n = {n_lines:d}$
- Total weld length:  $L_{{\\text{{total}}}} = n \\times L = {n_lines:d} \\times {weld_length:.2f} = {L_total:.2f}\\,\\text{{in}}$
- Applied shear on weld group:  $R_u = {Ru:.2f}\\,\\text{{kips}}$
"""
)

st.subheader("2. Effective Throat Thickness")

st.latex(r"t = 0.707\,w")
st.latex(
    rf"t = 0.707 \times {weld_size:.3f}\,\text{{in}} = {t:.3f}\,\text{{in}}"
)
st.caption("Reference: AISC-type fillet weld effective throat relation (leg-to-throat factor 0.707).")

st.subheader("3. Nominal Weld Strength per Unit Length")

st.latex(r"F_w = 0.6\,F_{EXX}")
st.latex(
    rf"F_w = 0.6 \times {F_exx:.1f}\,\text{{ksi}} = {Fw:.1f}\,\text{{ksi}}"
)

st.latex(r"r_n = F_w\,t = 0.6\,F_{EXX}\,t")
st.latex(
    rf"r_n = {Fw:.1f}\,\text{{ksi}} \times {t:.3f}\,\text{{in}} "
    rf"= {rn_per_length:.2f}\,\text{{kips/in}}"
)

st.caption("Reference: AISC 360-style nominal weld strength in shear (per unit length).")

st.subheader("4. Total Nominal Strength of Weld Group")

st.latex(r"L_{\text{total}} = n \, L")
st.latex(
    rf"L_{{\text{{total}}}} = {n_lines:d} \times {weld_length:.2f}\,\text{{in}} "
    rf"= {L_total:.2f}\,\text{{in}}"
)

st.latex(r"R_n = r_n \, L_{\text{total}}")
st.latex(
    rf"R_n = {rn_per_length:.2f}\,\text{{kips/in}} \times {L_total:.2f}\,\text{{in}} "
    rf"= {Rn:.2f}\,\text{{kips}}"
)

if design_method == "LRFD":
    st.subheader("5. LRFD Design Strength and Check")
    st.latex(r"\phi = 0.75")
    st.latex(r"\phi R_n = 0.75\,R_n")
    st.latex(
        rf"\phi R_n = 0.75 \times {Rn:.2f}\,\text{{kips}} = {R_design:.2f}\,\text{{kips}}"
    )
    st.latex(
        rf"\text{{Interaction ratio}} = \dfrac{{R_u}}{{\phi R_n}} "
        rf"= \dfrac{{{Ru:.2f}}}{{{R_design:.2f}}} = {utilization:.2f}"
    )
    st.caption("Reference: AISC 360-type LRFD weld design, φ ≈ 0.75 for welds in shear.")
else:
    st.subheader("5. ASD Allowable Strength and Check")
    st.latex(r"\Omega = 2.0")
    st.latex(r"R_{\text{allow}} = \dfrac{R_n}{\Omega}")
    st.latex(
        rf"R_{{\text{{allow}}}} = \dfrac{{{Rn:.2f}\,\text{{kips}}}}{{2.0}} "
        rf"= {R_design:.2f}\,\text{{kips}}"
    )
    st.latex(
        rf"\text{{Interaction ratio}} = \dfrac{{R_u}}{{R_{{\text{{allow}}}}}} "
        rf"= \dfrac{{{Ru:.2f}}}{{{R_design:.2f}}} = {utilization:.2f}"
    )
    st.caption("Reference: AISC 360-type ASD weld design, Ω ≈ 2.0 for welds in shear.")

st.markdown(
    """
---
**Notes**

- This sheet focuses on basic fillet weld shear capacity.  
- It does **not** consider direction of loading, combined stresses, or special seismic provisions.  
- Always verify against the latest AISC Specification and your project’s governing codes.
"""
)
