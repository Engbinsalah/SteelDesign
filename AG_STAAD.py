
import streamlit as st
import pandas as pd

# ==========================================
# 1. DATA (Hardcoded from STAAD Report)
# ==========================================
member_data = {
    "id": "1",
    "profile": "ST W8X31",
    "status": "PASS",
    "ratio": 0.218,
    "loadcase": "1006",
    "ref": "Eq.H1-1b",
    "location": 0.00,
    "forces": {
        "Pz": {"value": 6.830, "unit": "kips", "desc": "Axial Compression"},
        "Vy": {"value": -1.970, "unit": "kips", "desc": "Shear Y"},
        "Vx": {"value": -0.2474, "unit": "kips", "desc": "Shear X"},
        "Tz": {"value": -2.469, "unit": "kip-in", "desc": "Torsion"},
        "My": {"value": 9.130, "unit": "kip-in", "desc": "Moment Y"},
        "Mx": {"value": -243.2, "unit": "kip-in", "desc": "Moment X"}
    },
    "slenderness": {
        "actual": 87.309,
        "allowable": 200.000
    },
    "properties": {
        "Ag": {"value": 9.130, "unit": "in²"},
        "Axx": {"value": 6.960, "unit": "in²"},
        "Ayy": {"value": 2.280, "unit": "in²"},
        "Ixx": {"value": 110.0, "unit": "in⁴"},
        "Iyy": {"value": 37.10, "unit": "in⁴"},
        "J": {"value": 0.536, "unit": "in⁴"},
        "Sxx": {"value": 27.50, "unit": "in³"},
        "Zxx": {"value": 30.40, "unit": "in³"},
        "Syy": {"value": 9.275, "unit": "in³"},
        "Zyy": {"value": 14.10, "unit": "in³"},
        "Cw": {"value": 531.1, "unit": "in⁶"},
    },
    "material": {
        "Fyld": 50.000,
        "Fu": 62.000
    },
    "params": {
        "Length": 121.000,
        "Kx": 2.00,
        "Ky": 2.00,
        "Cb": 1.00
    },
    "checks": {
        "tension_yielding": {
            "demand": 0.000, "capacity": 410.9, "ratio": 0.000, "ref": "Cl.D2", "Pn": 456.50, "eqn": "Eq.D2-1"
        },
        "tension_rupture": {
            "demand": 0.000, "capacity": 424.5, "ratio": 0.000, "ref": "Cl.D2", "Ae": 9.1300, "Pn": 566.06, "eqn": "Eq.D2-2"
        },
        "compression_x": {
            "demand": 8.409, "capacity": 319.2, "ratio": 0.026, "ref": "Cl.E3", 
            "Lcx_rx": 58.772, "Fex": 82.863, "Fcrx": 38.841, "Pnx": 354.61
        },
        "compression_y": {
            "demand": 8.409, "capacity": 235.3, "ratio": 0.036, "ref": "Cl.E3", 
            "Lcy_ry": 87.309, "Fey": 37.547, "Fcry": 28.636, "Pny": 261.44
        },
        "shear_x": {
            "demand": 1.360, "capacity": 187.9, "ratio": 0.007, "ref": "Cl.G1",
            "Cv": 1.0000, "Vnx": 208.80
        },
        "shear_y": {
            "demand": 1.970, "capacity": 68.40, "ratio": 0.029, "ref": "Cl.G1",
            "Cv": 1.0000, "Vny": 68.400
        },
        "ltb_x": { 
            "demand": -243.2, "capacity": 1284.0, "ratio": 0.189, "ref": "Cl.F2.2",
            "Mnx": 1426.5, "Cb": 1.000, "Lp": 85.443, "Lr": 297.38
        },
        "flexure_y": {
            "demand": -83.49, "capacity": 634.5, "ratio": 0.132, "ref": "Cl.F6.1",
            "Mny": 705.00
        },
        "interaction": {
            "ratio": 0.218, "criteria": "Eq.H1-1b",
            "Pc": 235.30, "Mcx": 1283.8, "Mcy": 633.50
        }
    }
}

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def render_latex(lhs, rhs, subs=None, ref=None):
    """
    Renders a LaTeX equation with an optional substitution step.
    Uses \\times for multiplication.
    """
    # Replace standard python multiplication * with \times for display if present in string
    # But usually we write the latex string manually.
    
    # Display the Reference if provided
    if ref:
        st.markdown(f"**Reference:** {ref}")

    st.latex(f"{lhs} = {rhs}")
    
    if subs:
        sub_rhs = rhs
        for key, value in subs.items():
            # Replace variable with value
            # We use a simple replacement here. 
            # To ensure we don't replace partial words, we could use regex, but for this specific set of vars it's likely fine.
            # We will try to be careful.
            sub_rhs = sub_rhs.replace(key, f"{value}")
            
        st.markdown(f"*Substitution:*")
        st.latex(f"{lhs} = {sub_rhs}")

def section_header(title):
    st.markdown(f"### {title}")
    st.markdown("---")

def result_card(label, value, unit, status=None):
    color = "green" if status == "PASS" else "red" if status == "FAIL" else "black"
    st.markdown(
        f"""
        <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px; background-color: #f9f9f9;">
            <strong>{label}</strong>: {value} {unit} 
            {f'<span style="color:{color}; font-weight:bold; float:right">{status}</span>' if status else ''}
        </div>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# 3. STREAMLIT APP LAYOUT
# ==========================================
st.set_page_config(page_title="STAAD Design Calculation", layout="wide")

# Custom CSS for a clean report look
st.markdown("""
<style>
    .main { background-color: #ffffff; color: #333; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stApp { background-color: #f0f2f6; }
    h1, h2, h3 { color: #2c3e50; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("STAAD.Pro Design Calculation Sheet")
st.subheader("AISC 360-16 LRFD Code Check")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Member No", member_data["id"])
col2.metric("Profile", member_data["profile"])
col3.metric("Load Case", member_data["loadcase"])
col4.metric("Status", member_data["status"], delta=str(member_data["ratio"]), delta_color="inverse")

st.markdown("---")

# --- 1. Design Inputs ---
st.header("1. Design Inputs")

# 1.1 Applied Loads Table
st.subheader("1.1 Applied Loads")
loads = member_data["forces"]
load_table_data = []
for key, data in loads.items():
    load_table_data.append({
        "Load": key,
        "Value": data["value"],
        "Unit": data["unit"],
        "Definition": data["desc"]
    })
df_loads = pd.DataFrame(load_table_data)
st.table(df_loads)

# 1.2 Section Properties & Material
c1, c2 = st.columns(2)

with c1:
    st.subheader("1.2 Section Properties")
    props = member_data["properties"]
    prop_table_data = [{"Property": k, "Value": v["value"], "Unit": v["unit"]} for k, v in props.items()]
    st.table(pd.DataFrame(prop_table_data))

with c2:
    st.subheader("1.3 Material & Parameters")
    mat = member_data["material"]
    par = member_data["params"]
    
    st.markdown("**Material Properties**")
    st.write(f"- Yield Strength ($F_y$): {mat['Fyld']} ksi")
    st.write(f"- Ultimate Strength ($F_u$): {mat['Fu']} ksi")
    
    st.markdown("**Design Parameters**")
    st.write(f"- Length: {par['Length']} in")
    st.write(f"- Effective Length Factors: $K_x={par['Kx']}, K_y={par['Ky']}$")
    st.write(f"- LTB Modification Factor ($C_b$): {par['Cb']}")

# --- 2. Detailed Calculations ---
st.header("2. Detailed Calculations")

# 2.1 Tension
section_header("2.1 Tension Checks")
t_yield = member_data["checks"]["tension_yielding"]
t_rupture = member_data["checks"]["tension_rupture"]

st.markdown("#### Tensile Yielding")
render_latex(
    lhs="P_n", 
    rhs="F_y \\times A_g", 
    subs={"F_y": member_data["material"]["Fyld"], "A_g": member_data["properties"]["Ag"]["value"]},
    ref=f"{t_yield['ref']} ({t_yield['eqn']})"
)
st.write(f"**Capacity ($P_n$):** {t_yield['Pn']} kips")
result_card("Ratio", t_yield["ratio"], "", "PASS" if t_yield["ratio"] < 1.0 else "FAIL")

st.markdown("#### Tensile Rupture")
render_latex(
    lhs="P_n", 
    rhs="F_u \\times A_e", 
    subs={"F_u": member_data["material"]["Fu"], "A_e": t_rupture["Ae"]},
    ref=f"{t_rupture['ref']} ({t_rupture['eqn']})"
)
st.write(f"**Capacity ($P_n$):** {t_rupture['Pn']} kips")
result_card("Ratio", t_rupture["ratio"], "", "PASS" if t_rupture["ratio"] < 1.0 else "FAIL")


# 2.2 Compression
section_header("2.2 Compression Checks")
comp_x = member_data["checks"]["compression_x"]
comp_y = member_data["checks"]["compression_y"]

st.markdown("#### Flexural Buckling (X-Axis)")
st.write(f"Effective Slenderness ($L_{{cx}}/r_x$): {comp_x['Lcx_rx']}")
render_latex(
    lhs="F_{crx}",
    rhs="0.658^{F_y/F_{ex}} \\times F_y",
    subs={"F_y": member_data["material"]["Fyld"], "F_{ex}": comp_x["Fex"]},
    ref=f"{comp_x['ref']} (Eq.E3-2)"
)
st.write(f"**Critical Stress ($F_{{crx}}$):** {comp_x['Fcrx']} ksi")
render_latex(
    lhs="P_{nx}",
    rhs="F_{crx} \\times A_g",
    subs={"F_{crx}": comp_x["Fcrx"], "A_g": member_data["properties"]["Ag"]["value"]},
    ref="Eq.E3-1"
)
st.write(f"**Capacity ($P_{{nx}}$):** {comp_x['Pnx']} kips")
result_card("Ratio", comp_x["ratio"], "", "PASS" if comp_x["ratio"] < 1.0 else "FAIL")

st.markdown("#### Flexural Buckling (Y-Axis)")
st.write(f"Effective Slenderness ($L_{{cy}}/r_y$): {comp_y['Lcy_ry']}")
render_latex(
    lhs="F_{cry}",
    rhs="0.658^{F_y/F_{ey}} \\times F_y",
    subs={"F_y": member_data["material"]["Fyld"], "F_{ey}": comp_y["Fey"]},
    ref=f"{comp_y['ref']} (Eq.E3-2)"
)
st.write(f"**Critical Stress ($F_{{cry}}$):** {comp_y['Fcry']} ksi")
render_latex(
    lhs="P_{ny}",
    rhs="F_{cry} \\times A_g",
    subs={"F_{cry}": comp_y["Fcry"], "A_g": member_data["properties"]["Ag"]["value"]},
    ref="Eq.E3-1"
)
st.write(f"**Capacity ($P_{{ny}}$):** {comp_y['Pny']} kips")
result_card("Ratio", comp_y["ratio"], "", "PASS" if comp_y["ratio"] < 1.0 else "FAIL")


# 2.3 Shear
section_header("2.3 Shear Checks")
shear_x = member_data["checks"]["shear_x"]
shear_y = member_data["checks"]["shear_y"]

c_s1, c_s2 = st.columns(2)
with c_s1:
    st.markdown("#### Shear Along X")
    render_latex(
        lhs="V_{nx}",
        rhs="0.6 \\times F_y \\times A_w \\times C_v",
        subs={"F_y": member_data["material"]["Fyld"], "A_w": "Aw", "C_v": shear_x["Cv"]},
        ref=f"{shear_x['ref']} (Eq.G2-1)"
    )
    st.write(f"**Capacity ($V_{{nx}}$):** {shear_x['Vnx']} kips")
    result_card("Ratio", shear_x["ratio"], "", "PASS" if shear_x["ratio"] < 1.0 else "FAIL")

with c_s2:
    st.markdown("#### Shear Along Y")
    render_latex(
        lhs="V_{ny}",
        rhs="0.6 \\times F_y \\times A_w \\times C_v",
        subs={"F_y": member_data["material"]["Fyld"], "A_w": "Aw", "C_v": shear_y["Cv"]},
        ref=f"{shear_y['ref']} (Eq.G2-1)"
    )
    st.write(f"**Capacity ($V_{{ny}}$):** {shear_y['Vny']} kips")
    result_card("Ratio", shear_y["ratio"], "", "PASS" if shear_y["ratio"] < 1.0 else "FAIL")


# 2.4 Bending
section_header("2.4 Bending Checks")
ltb_x = member_data["checks"]["ltb_x"]
flex_y = member_data["checks"]["flexure_y"]

st.markdown("#### X-Axis: Lateral Torsional Buckling")
st.write(f"Unbraced Length ($L_b$): {member_data['params']['Length']} in")
st.write(f"Limiting Lengths: $L_p = {ltb_x['Lp']}$ in, $L_r = {ltb_x['Lr']}$ in")
render_latex(
    lhs="M_{nx}",
    rhs="C_b \\times [M_p - (M_p - 0.7 \\times F_y \\times S_x) \\times \\frac{L_b - L_p}{L_r - L_p}]",
    subs={"C_b": ltb_x["Cb"], "M_p": "Mp", "F_y": member_data["material"]["Fyld"]},
    ref=f"{ltb_x['ref']} (Eq.F2-2)"
)
st.write(f"**Capacity ($M_{{nx}}$):** {ltb_x['Mnx']} kip-in")
result_card("Ratio", ltb_x["ratio"], "", "PASS" if ltb_x["ratio"] < 1.0 else "FAIL")

st.markdown("#### Y-Axis: Flexural Yielding")
render_latex(
    lhs="M_{ny}",
    rhs="M_p = F_y \\times Z_y",
    subs={"F_y": member_data["material"]["Fyld"], "Z_y": member_data["properties"]["Zyy"]["value"]},
    ref=f"{flex_y['ref']} (Eq.F6-1)"
)
st.write(f"**Capacity ($M_{{ny}}$):** {flex_y['Mny']} kip-in")
result_card("Ratio", flex_y["ratio"], "", "PASS" if flex_y["ratio"] < 1.0 else "FAIL")


# 2.5 Interaction
section_header("2.5 Interaction Checks")
inter = member_data["checks"]["interaction"]

st.markdown("#### Combined Axial and Flexure")
st.info("Applicable when $P_r / P_c < 0.2$")

render_latex(
    lhs="Ratio",
    rhs="\\frac{P_r}{2P_c} + (\\frac{M_{rx}}{M_{cx}} + \\frac{M_{ry}}{M_{cy}})",
    subs={
        "P_r": member_data["forces"]["Pz"]["value"], "P_c": inter["Pc"],
        "M_{rx}": abs(member_data["forces"]["Mx"]["value"]), "M_{cx}": inter["Mcx"],
        "M_{ry}": member_data["forces"]["My"]["value"], "M_{cy}": inter["Mcy"]
    },
    ref=f"{inter['criteria']}"
)

st.metric("Final Interaction Ratio", inter["ratio"])
if inter["ratio"] <= 1.0:
    st.success(f"Member PASSES with Ratio {inter['ratio']}")
else:
    st.error(f"Member FAILS with Ratio {inter['ratio']}")
