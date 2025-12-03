import streamlit as st
import pandas as pd
import re
import math

# ==========================================
# 1. CONFIG & CSS
# ==========================================
st.set_page_config(page_title="STAAD Design Check (Auto-Calc)", layout="wide")

st.markdown("""
<style>
    .main { background-color: #ffffff; color: #333; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    h1, h2, h3 { color: #2c3e50; }
    .stTextArea textarea { font-family: 'Consolas', 'Courier New', monospace; font-size: 14px; }
    .stAlert { padding: 10px; border-radius: 5px; }
    .metric-card { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; }
    .metric-label { font-size: 14px; color: #6c757d; margin-bottom: 5px; }
    .metric-value { font-size: 24px; font-weight: 600; color: #2c3e50; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def format_val(val, decimals=2):
    try:
        f_val = float(val)
        if abs(f_val) < 1 and f_val != 0:
            return f"{f_val:.3f}"
        return f"{f_val:.{decimals}f}"
    except (ValueError, TypeError):
        return str(val)

def render_latex(lhs, rhs, subs=None, ref=None):
    if ref:
        st.markdown(f"**Reference:** {ref}")
    st.latex(f"{lhs} = {rhs}")
    if subs:
        sub_rhs = rhs
        for key, value in subs.items():
            sub_rhs = sub_rhs.replace(key, f"{value}")
        st.latex(f"{lhs} = {sub_rhs}")

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

def parse_value(line, key):
    """Helper to extract value after a key (e.g., 'Pz:')"""
    pattern = re.escape(key) + r"\s*[:=]\s*([-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?)"
    match = re.search(pattern, line, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None

# ==========================================
# 3. PARSING LOGIC (INPUTS ONLY)
# ==========================================
def parse_staad_inputs(text):
    data = {
        "id": "Unknown", "profile": "Unknown", "loadcase": "Unknown",
        "forces": {}, "properties": {}, "material": {}, "params": {}, "classification": {}
    }
    
    # Defaults
    data["params"] = {"Kx": 1.0, "Ky": 1.0, "Cb": 1.0, "NSF": 1.0, "SLF": 1.0, "CSP": 0.0, "Length": 0.0}
    data["material"] = {"Fyld": 50.0, "Fu": 65.0}
    
    lines = text.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Header Info
        if "Member No:" in line:
            m = re.search(r"Member No:\s+(\d+)", line)
            if m: data["id"] = m.group(1)
            m = re.search(r"Profile:\s+(.*?)\s+\(", line)
            if m: data["profile"] = m.group(1).strip()
        if "Loadcase:" in line:
            m = re.search(r"Loadcase:\s+(\d+)", line)
            if m: data["loadcase"] = m.group(1)
            
        # Forces
        if "Pz:" in line:
            data["forces"]["Pz"] = parse_value(line, "Pz")
            data["forces"]["Vy"] = parse_value(line, "Vy")
            data["forces"]["Vx"] = parse_value(line, "Vx")
        if "Tz:" in line:
            data["forces"]["Tz"] = parse_value(line, "Tz")
            data["forces"]["My"] = parse_value(line, "My")
            data["forces"]["Mx"] = parse_value(line, "Mx")
            
        # Properties
        if "Ag" in line and (":" in line or "=" in line):
            data["properties"]["Ag"] = parse_value(line, "Ag")
            data["properties"]["Axx"] = parse_value(line, "Axx")
            data["properties"]["Ayy"] = parse_value(line, "Ayy")
        if "Ixx" in line and (":" in line or "=" in line):
            data["properties"]["Ixx"] = parse_value(line, "Ixx")
            data["properties"]["Iyy"] = parse_value(line, "Iyy")
            data["properties"]["J"] = parse_value(line, "J")
        if "Sxx" in line and (":" in line or "=" in line):
            data["properties"]["Sxx"] = parse_value(line, "Sxx+") 
            data["properties"]["Zxx"] = parse_value(line, "Zxx")
        if "Syy" in line and (":" in line or "=" in line):
            data["properties"]["Syy"] = parse_value(line, "Syy+")
            data["properties"]["Zyy"] = parse_value(line, "Zyy")
        if "Cw" in line and (":" in line or "=" in line):
            data["properties"]["Cw"] = parse_value(line, "Cw")
            
        # Material
        if "Fyld:" in line or "Fyld" in line:
            val = parse_value(line, "Fyld")
            if val: data["material"]["Fyld"] = val
            val = parse_value(line, "Fu")
            if val: data["material"]["Fu"] = val
            
        # Parameters
        if "Actual Member Length:" in line:
            data["params"]["Length"] = parse_value(line, "Actual Member Length")
        if "Kx:" in line:
            data["params"]["Kx"] = parse_value(line, "Kx")
            data["params"]["Ky"] = parse_value(line, "Ky")
            data["params"]["NSF"] = parse_value(line, "NSF")
            data["params"]["SLF"] = parse_value(line, "SLF")
            data["params"]["CSP"] = parse_value(line, "CSP")
            
        # Classification
        if "COMPRESSION CLASSIFICATION" in line: current_section = "class_comp"
        elif "FLEXURE CLASSIFICATION" in line: current_section = "class_flex"
        
        if current_section == "class_comp":
            if "Flange:" in line:
                m = re.search(r"Flange:\s+(\w+)\s+([\d.]+)", line)
                if m: 
                    if "compression" not in data["classification"]: data["classification"]["compression"] = {}
                    data["classification"]["compression"]["flange"] = {"status": m.group(1), "lambda": float(m.group(2))}
            if "Web" in line and ":" in line:
                m = re.search(r"Web\s*:\s+(\w+)\s+([\d.]+)", line)
                if m:
                    if "compression" not in data["classification"]: data["classification"]["compression"] = {}
                    data["classification"]["compression"]["web"] = {"status": m.group(1), "lambda": float(m.group(2))}

        if current_section == "class_flex":
            if "Flange:" in line:
                m = re.search(r"Flange:\s+(\w+)\s+([\d.]+)", line)
                if m: 
                    if "flexure" not in data["classification"]: data["classification"]["flexure"] = {}
                    data["classification"]["flexure"]["flange"] = {"status": m.group(1), "lambda": float(m.group(2))}
            if "Web" in line and ":" in line:
                m = re.search(r"Web\s*:\s+(\w+)\s+([\d.]+)", line)
                if m:
                    if "flexure" not in data["classification"]: data["classification"]["flexure"] = {}
                    data["classification"]["flexure"]["web"] = {"status": m.group(1), "lambda": float(m.group(2))}

    return data

# ==========================================
# 4. CALCULATION ENGINE
# ==========================================
def calculate_checks(data):
    results = {}
    
    # Inputs
    E = 29000.0
    G = 11200.0
    Fy = data["material"]["Fyld"]
    Fu = data["material"]["Fu"]
    
    props = data["properties"]
    Ag = props.get("Ag", 0)
    Ixx = props.get("Ixx", 0)
    Iyy = props.get("Iyy", 0)
    J = props.get("J", 0)
    Cw = props.get("Cw", 0)
    Sxx = props.get("Sxx", 0)
    Syy = props.get("Syy", 0)
    Zxx = props.get("Zxx", 0)
    Zyy = props.get("Zyy", 0)
    Axx = props.get("Axx", 0) # Shear area X
    Ayy = props.get("Ayy", 0) # Shear area Y
    
    params = data["params"]
    L = params.get("Length", 0)
    Kx = params.get("Kx", 1.0)
    Ky = params.get("Ky", 1.0)
    Cb = params.get("Cb", 1.0)
    NSF = params.get("NSF", 1.0)
    SLF = params.get("SLF", 1.0)
    
    forces = data["forces"]
    Pu = abs(forces.get("Pz", 0))
    Vux = abs(forces.get("Vx", 0))
    Vuy = abs(forces.get("Vy", 0))
    Mux = abs(forces.get("Mx", 0))
    Muy = abs(forces.get("My", 0))
    
    # Derived
    rx = (Ixx/Ag)**0.5 if Ag > 0 else 0
    ry = (Iyy/Ag)**0.5 if Ag > 0 else 0
    # Approx h0 from Cw = Iy * h0^2 / 4 => h0 = sqrt(4*Cw/Iy)
    h0 = (4 * Cw / Iyy)**0.5 if Iyy > 0 else 0
    
    # --- TENSION ---
    # Yielding
    Pn_yield = Fy * Ag
    phi_Pn_yield = 0.9 * Pn_yield
    results["tension_yielding"] = {"Pn": Pn_yield, "phi_Pn": phi_Pn_yield, "demand": Pu, "ratio": Pu/phi_Pn_yield if phi_Pn_yield else 0}
    
    # Rupture
    Ae = Ag * NSF * SLF # Simplified assumption based on params
    Pn_rup = Fu * Ae
    phi_Pn_rup = 0.75 * Pn_rup
    results["tension_rupture"] = {"Pn": Pn_rup, "phi_Pn": phi_Pn_rup, "demand": Pu, "ratio": Pu/phi_Pn_rup if phi_Pn_rup else 0, "Ae": Ae}
    
    # --- COMPRESSION ---
    # Flexural Buckling X
    KL_rx = (Kx * L) / rx if rx > 0 else 0
    Fex = (math.pi**2 * E) / (KL_rx**2) if KL_rx > 0 else 0
    if KL_rx <= 4.71 * (E/Fy)**0.5:
        Fcrx = (0.658**(Fy/Fex)) * Fy if Fex > 0 else 0
    else:
        Fcrx = 0.877 * Fex
    Pnx = Fcrx * Ag
    phi_Pnx = 0.9 * Pnx
    results["comp_x"] = {"Pn": Pnx, "phi_Pn": phi_Pnx, "demand": Pu, "ratio": Pu/phi_Pnx if phi_Pnx else 0, "KL_r": KL_rx, "Fe": Fex, "Fcr": Fcrx}
    
    # Flexural Buckling Y
    KL_ry = (Ky * L) / ry if ry > 0 else 0
    Fey = (math.pi**2 * E) / (KL_ry**2) if KL_ry > 0 else 0
    if KL_ry <= 4.71 * (E/Fy)**0.5:
        Fcry = (0.658**(Fy/Fey)) * Fy if Fey > 0 else 0
    else:
        Fcry = 0.877 * Fey
    Pny = Fcry * Ag
    phi_Pny = 0.9 * Pny
    results["comp_y"] = {"Pn": Pny, "phi_Pn": phi_Pny, "demand": Pu, "ratio": Pu/phi_Pny if phi_Pny else 0, "KL_r": KL_ry, "Fe": Fey, "Fcr": Fcry}
    
    # FTB
    # Assuming doubly symmetric, xo=yo=0
    ro2 = (Ixx + Iyy)/Ag # xo=yo=0
    H = 1.0
    Kz = 1.0 # Assume 1.0
    Lcz = Kz * L
    term1 = (math.pi**2 * E * Cw) / (Lcz**2) if Lcz > 0 else 0
    term2 = G * J
    Fez = (term1 + term2) * (1/(Ag * ro2)) if (Ag*ro2) > 0 else 0
    
    # Fe is min of roots of quadratic, but for doubly symmetric, Fe = Fez (Torsional) or Fex/Fey.
    # AISC E4: For doubly symmetric, FTB is purely Torsional (Fez) or Flexural.
    # Usually we check Torsional vs Flexural.
    # The code usually takes Fe = Fez for Torsional Buckling of doubly symmetric.
    Fe_ftb = Fez
    # Use lowest Fe for Fcr calculation
    # Actually, for doubly symmetric, we check Flexural (X, Y) and Torsional (Z).
    # The "FTB" section in STAAD for W-shapes usually refers to Torsional Buckling (E4).
    if Fe_ftb > 0:
        if (Fy/Fe_ftb) <= 2.25:
            Fcr_ftb = (0.658**(Fy/Fe_ftb)) * Fy
        else:
            Fcr_ftb = 0.877 * Fe_ftb
    else:
        Fcr_ftb = 0
        
    Pn_ftb = Fcr_ftb * Ag
    phi_Pn_ftb = 0.9 * Pn_ftb
    results["ftb"] = {"Pn": Pn_ftb, "phi_Pn": phi_Pn_ftb, "demand": Pu, "ratio": Pu/phi_Pn_ftb if phi_Pn_ftb else 0, "Fe": Fe_ftb, "Fcr": Fcr_ftb, "Fez": Fez, "H": H, "ro2": ro2}

    # --- SHEAR ---
    # Shear X (Weak Axis Shear?) - Depends on Axx.
    # AISC G2.1: Vn = 0.6 Fy Aw Cv1.
    # Assuming rolled I-shape, h/tw check for Cv.
    # Without h/tw, we assume Cv=1.0 if "NonSlender".
    Cv = 1.0
    Vnx = 0.6 * Fy * Axx * Cv
    phi_Vnx = 0.9 * Vnx # LRFD phi=0.9 for shear
    results["shear_x"] = {"Vn": Vnx, "phi_Vn": phi_Vnx, "demand": Vux, "ratio": Vux/phi_Vnx if phi_Vnx else 0, "Cv": Cv}
    
    Vny = 0.6 * Fy * Ayy * Cv
    phi_Vny = 0.9 * Vny
    results["shear_y"] = {"Vn": Vny, "phi_Vn": phi_Vny, "demand": Vuy, "ratio": Vuy/phi_Vny if phi_Vny else 0, "Cv": Cv}
    
    # --- BENDING ---
    # Flexural Yielding (Y-Axis - Minor)
    Mny_yield = Fy * Zyy
    if Mny_yield > 1.6 * Fy * Syy: Mny_yield = 1.6 * Fy * Syy
    phi_Mny = 0.9 * Mny_yield
    results["flex_y"] = {"Mn": Mny_yield, "phi_Mn": phi_Mny, "demand": Muy, "ratio": Muy/phi_Mny if phi_Mny else 0}
    
    # LTB (X-Axis - Major)
    # Lp = 1.76 ry sqrt(E/Fy)
    Lp = 1.76 * ry * (E/Fy)**0.5 if ry > 0 else 0
    
    # Lr
    # rts = sqrt( sqrt(Iy Cw) / Sx )
    rts = ((Iyy * Cw)**0.5 / Sxx)**0.5 if Sxx > 0 else 0
    
    # c = 1 for doubly symmetric I
    c = 1.0
    # ho = distance between flange centroids
    
    if rts > 0 and h0 > 0:
        term_lr1 = 1.95 * rts * E / (0.7 * Fy)
        term_lr2 = (J * c) / (Sxx * h0)
        term_lr3 = (term_lr2**2 + 6.76 * (0.7 * Fy / E)**2)**0.5
        Lr = term_lr1 * (term_lr2 + term_lr3)**0.5
    else:
        Lr = 0
        
    Mn_ltb = 0
    Mp = Fy * Zxx
    
    Lb = L # Unbraced length
    
    if Lb <= Lp:
        Mn_ltb = Mp
    elif Lb > Lp and Lb <= Lr:
        Mn_ltb = Cb * (Mp - (Mp - 0.7*Fy*Sxx) * (Lb - Lp)/(Lr - Lp))
        if Mn_ltb > Mp: Mn_ltb = Mp
    else:
        Fcr_ltb = (Cb * math.pi**2 * E) / ((Lb/rts)**2) * (1 + 0.078 * (J*c)/(Sxx*h0) * (Lb/rts)**2)**0.5
        Mn_ltb = Fcr_ltb * Sxx
        if Mn_ltb > Mp: Mn_ltb = Mp
        
    phi_Mnx = 0.9 * Mn_ltb
    results["ltb_x"] = {"Mn": Mn_ltb, "phi_Mn": phi_Mnx, "demand": Mux, "ratio": Mux/phi_Mnx if phi_Mnx else 0, "Lp": Lp, "Lr": Lr, "Rts": rts, "Cb": Cb}
    
    # FLB (X)
    # Assume Compact for now or use classification
    # If Compact, Mn = Mp
    # User input says "Flange: Compact".
    Mn_flb_x = Mp
    phi_Mn_flb_x = 0.9 * Mn_flb_x
    results["flb_x"] = {"Mn": Mn_flb_x, "phi_Mn": phi_Mn_flb_x, "demand": Mux, "ratio": Mux/phi_Mn_flb_x if phi_Mn_flb_x else 0}
    
    # FLB (Y)
    Mn_flb_y = Mny_yield
    phi_Mn_flb_y = 0.9 * Mn_flb_y
    results["flb_y"] = {"Mn": Mn_flb_y, "phi_Mn": phi_Mn_flb_y, "demand": Muy, "ratio": Muy/phi_Mn_flb_y if phi_Mn_flb_y else 0}
    
    # --- INTERACTION ---
    # H1-1
    # Pr = Pu, Pc = phi_Pn (min of comp checks)
    Pc = min(phi_Pnx, phi_Pny, phi_Pn_ftb)
    Mcx = min(phi_Mnx, phi_Mn_flb_x)
    Mcy = min(phi_Mny, phi_Mn_flb_y)
    
    Pr_Pc = Pu / Pc if Pc > 0 else 0
    
    if Pr_Pc >= 0.2:
        ratio = Pr_Pc + 8/9 * (Mux/Mcx + Muy/Mcy)
        eqn = "Eq.H1-1a"
    else:
        ratio = Pr_Pc/2 + (Mux/Mcx + Muy/Mcy)
        eqn = "Eq.H1-1b"
        
    results["interaction"] = {"ratio": ratio, "eqn": eqn, "Pc": Pc, "Mcx": Mcx, "Mcy": Mcy}
    
    return results

# ==========================================
# 5. UI & MAIN
# ==========================================
st.title("STAAD Design Check (Auto-Calc)")

default_input = """...""" # (User's input here)

input_text = st.text_area("Paste STAAD Output (Inputs Only)", height=300)

if input_text:
    data = parse_staad_inputs(input_text)
    
    if data["id"] != "Unknown":
        # Calculate
        res = calculate_checks(data)
        
        # Display Header
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Member", data["id"])
        c2.metric("Profile", data["profile"])
        c3.metric("Load Case", data["loadcase"])
        c4.metric("Interaction Ratio", f"{res['interaction']['ratio']:.3f}", delta_color="inverse" if res['interaction']['ratio'] >= 1 else "normal")
        
        st.markdown("---")
        
        # Display Inputs
        st.subheader("1. Inputs")
        c_in1, c_in2 = st.columns(2)
        with c_in1:
            st.markdown("**Forces**")
            st.write(f"Pz (Axial): {data['forces'].get('Pz')} kips")
            st.write(f"Vx, Vy (Shear): {data['forces'].get('Vx')}, {data['forces'].get('Vy')} kips")
            st.write(f"Mx, My (Moment): {data['forces'].get('Mx')}, {data['forces'].get('My')} kip-in")
        with c_in2:
            st.markdown("**Properties**")
            st.write(f"Ag: {data['properties'].get('Ag')} in²")
            st.write(f"Ixx: {data['properties'].get('Ixx')} in⁴, Iyy: {data['properties'].get('Iyy')} in⁴")
            st.write(f"Cw: {data['properties'].get('Cw')} in⁶, J: {data['properties'].get('J')} in⁴")
            
        st.markdown("---")
        st.subheader("2. Detailed Checks")
        
        # Tension
        st.markdown("### 2.1 Tension")
        t_y = res["tension_yielding"]
        st.markdown("**Tensile Yielding**")
        render_latex("P_n", "F_y A_g", {"F_y": data["material"]["Fyld"], "A_g": data["properties"]["Ag"]})
        st.latex(f"P_n = {format_val(t_y['Pn'])} \\text{{ kips}}")
        st.latex(f"\phi P_n = {format_val(t_y['phi_Pn'])} \\text{{ kips}}")
        result_card("Ratio", t_y["ratio"], "", "PASS" if t_y["ratio"] < 1 else "FAIL")
        
        t_r = res["tension_rupture"]
        st.markdown("**Tensile Rupture**")
        render_latex("P_n", "F_u A_e", {"F_u": data["material"]["Fu"], "A_e": f"{t_r['Ae']:.2f}"})
        st.latex(f"P_n = {format_val(t_r['Pn'])} \\text{{ kips}}")
        st.latex(f"\phi P_n = {format_val(t_r['phi_Pn'])} \\text{{ kips}}")
        result_card("Ratio", t_r["ratio"], "", "PASS" if t_r["ratio"] < 1 else "FAIL")
        
        # Compression
        st.markdown("### 2.2 Compression")
        c_c1, c_c2 = st.columns(2)
        with c_c1:
            cx = res["comp_x"]
            st.markdown("**Flexural Buckling (X)**")
            st.write(f"KL/r: {cx['KL_r']:.2f}")
            st.latex(f"F_{{ex}} = {format_val(cx['Fe'])} \\text{{ ksi}}")
            st.latex(f"F_{{cr}} = {format_val(cx['Fcr'])} \\text{{ ksi}}")
            st.latex(f"\phi P_n = {format_val(cx['phi_Pn'])} \\text{{ kips}}")
            result_card("Ratio", cx["ratio"], "", "PASS" if cx["ratio"] < 1 else "FAIL")
            
        with c_c2:
            cy = res["comp_y"]
            st.markdown("**Flexural Buckling (Y)**")
            st.write(f"KL/r: {cy['KL_r']:.2f}")
            st.latex(f"F_{{ey}} = {format_val(cy['Fe'])} \\text{{ ksi}}")
            st.latex(f"F_{{cr}} = {format_val(cy['Fcr'])} \\text{{ ksi}}")
            st.latex(f"\phi P_n = {format_val(cy['phi_Pn'])} \\text{{ kips}}")
            result_card("Ratio", cy["ratio"], "", "PASS" if cy["ratio"] < 1 else "FAIL")
            
        # FTB
        ftb = res["ftb"]
        st.markdown("**Flexural-Torsional Buckling**")
        st.latex(f"F_e = {format_val(ftb['Fe'])} \\text{{ ksi}}")
        st.latex(f"F_{{cr}} = {format_val(ftb['Fcr'])} \\text{{ ksi}}")
        st.latex(f"\phi P_n = {format_val(ftb['phi_Pn'])} \\text{{ kips}}")
        result_card("Ratio", ftb["ratio"], "", "PASS" if ftb["ratio"] < 1 else "FAIL")
        
        # Shear
        st.markdown("### 2.3 Shear")
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            sx = res["shear_x"]
            st.markdown("**Shear X**")
            st.latex(f"\phi V_n = {format_val(sx['phi_Vn'])} \\text{{ kips}}")
            result_card("Ratio", sx["ratio"], "", "PASS" if sx["ratio"] < 1 else "FAIL")
        with c_s2:
            sy = res["shear_y"]
            st.markdown("**Shear Y**")
            st.latex(f"\phi V_n = {format_val(sy['phi_Vn'])} \\text{{ kips}}")
            result_card("Ratio", sy["ratio"], "", "PASS" if sy["ratio"] < 1 else "FAIL")
            
        # Bending
        st.markdown("### 2.4 Bending")
        c_b1, c_b2 = st.columns(2)
        with c_b1:
            ltb = res["ltb_x"]
            st.markdown("**LTB (X-Axis)**")
            st.write(f"Lp: {ltb['Lp']:.2f}, Lr: {ltb['Lr']:.2f}, Lb: {data['params']['Length']}")
            st.latex(f"\phi M_n = {format_val(ltb['phi_Mn'])} \\text{{ kip-in}}")
            result_card("Ratio", ltb["ratio"], "", "PASS" if ltb["ratio"] < 1 else "FAIL")
        with c_b2:
            fy = res["flex_y"]
            st.markdown("**Flexure (Y-Axis)**")
            st.latex(f"\phi M_n = {format_val(fy['phi_Mn'])} \\text{{ kip-in}}")
            result_card("Ratio", fy["ratio"], "", "PASS" if fy["ratio"] < 1 else "FAIL")
            
        # Interaction
        st.markdown("### 2.5 Interaction")
        inter = res["interaction"]
        st.write(f"Criteria: {inter['eqn']}")
        st.latex(f"P_c = {format_val(inter['Pc'])}, M_{{cx}} = {format_val(inter['Mcx'])}, M_{{cy}} = {format_val(inter['Mcy'])}")
        result_card("Interaction Ratio", inter["ratio"], "", "PASS" if inter["ratio"] < 1 else "FAIL")
        
    else:
        st.info("Paste STAAD output above to see calculations.")
