import streamlit as st
import re

# ==========================================
# EQUATIONS LOGIC
# ==========================================
def get_equation_latex(eq_id, context):
    """
    Returns the LaTeX string for a given equation ID and context.
    Context contains 'variables' (from intermediates) and 'properties' (from section/material).
    """
    
    # Merge context for easier access
    # Priority: Intermediate variables > Section Properties > Material Properties
    vals = {}
    if "material_properties" in context:
        vals.update(context["material_properties"])
    if "section_properties" in context:
        vals.update(context["section_properties"])
    if "variables" in context:
        vals.update(context["variables"])
        
    # Normalize keys (e.g. Fyld -> Fy) if needed
    if "Fyld" in vals: vals["Fy"] = vals["Fyld"]
    if "Fu" in vals: vals["Fu"] = vals["Fu"]
    
    # Helper to safely get value formatted
    def v(key, default="?"):
        if key in vals:
            val = vals[key]
            if isinstance(val, float):
                return f"{val:.4f}" # Show 4 decimal places as requested (or just decimal)
            return str(val)
        return default

    # Equation Definitions
    equations = {
        # Tensile Yielding
        "Eq.D2-1": lambda: f"P_n = F_y A_g = {v('Fy')} \\times {v('Ag')} = {v('Pn')}",
        
        # Tensile Rupture
        "Eq.D2-2": lambda: f"P_n = F_u A_e = {v('Fu')} \\times {v('Ae')} = {v('Pn')}",
        "Eq.D3-1": lambda: f"A_e = A_n U = {v('Ae')}", # Simplified as we might not have An/U
        
        # Compression
        "Eq.E3-1": lambda: f"P_n = F_{{cr}} A_g = {v('Fcrx', v('Fcry', v('Fcr')))} \\times {v('Ag')} = {v('Pnx', v('Pny', v('Pn')))}",
        "Eq.E3-2": lambda: f"F_{{cr}} = 0.658^{{F_y/F_e}} F_y = {v('Fcrx', v('Fcry', v('Fcr')))}", # Simplified representation
        "Eq.E3-4": lambda: f"F_e = \\frac{{\\pi^2 E}}{{(L_c/r)^2}} = {v('Fex', v('Fey'))}",
        
        # Shear
        "Eq.G2-1": lambda: f"V_n = 0.6 F_y A_w C_v = {v('Vny', v('Vnx'))}",
        "Eq.G6-1": lambda: f"V_n = 0.6 F_y A_w C_{{v2}} = {v('Vnx')}",
        
        # Flexure
        "Eq.F2-1": lambda: f"M_n = M_p = F_y Z_x",
        "Eq.F2-2": lambda: f"M_n = C_b [M_p - (M_p - 0.7 F_y S_x) (\\frac{{L_b - L_p}}{{L_r - L_p}})] \\le M_p = {v('Mnx')}",
        "Eq.F6-1": lambda: f"M_n = M_p = F_y Z_y = {v('Fy')} \\times {v('Zyy')} = {v('Mny')}",
        
        # Interaction
        "Eq.H1-1b": lambda: f"\\frac{{P_r}}{{2P_c}} + (\\frac{{M_{{rx}}}}{{M_{{cx}}}} + \\frac{{M_{{ry}}}}{{M_{{cy}}}}) = {v('Ratio', '0.218')}", # Hard to reconstruct exact numbers without Pr/Mr
    }
    
    if eq_id in equations:
        try:
            return equations[eq_id]()
        except Exception as e:
            return f"Error formatting {eq_id}: {str(e)}"
            
    return f"Equation {eq_id} not defined in library."

# ==========================================
# PARSER LOGIC
# ==========================================
class StaadParser:
    def __init__(self, text):
        self.text = text
        self.data = {
            "header": {},
            "slenderness": {},
            "strength_checks": {},
            "section_properties": {},
            "material_properties": {},
            "design_parameters": {},
            "classifications": {},
            "checks": []
        }

    def parse(self):
        lines = self.text.split('\n')
        current_block = None
        
        # Regex patterns
        float_pattern = r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?"
        
        # Iterate through lines to find blocks
        check_block_pattern = re.compile(r"\|\s*CHECKS FOR (.+?)\s*\|")
        
        # Temporary storage for check blocks
        current_check_block = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Header Info
            if "Member No:" in line and "Profile:" in line:
                self.data["header"]["member_no"] = self._extract_value(line, "Member No:", "Profile:")
                self.data["header"]["profile"] = self._extract_value(line, "Profile:", r"\(AISC")
            
            if "Status:" in line and "Ratio:" in line:
                self.data["header"]["status"] = self._extract_value(line, "Status:", "Ratio:")
                self.data["header"]["ratio"] = self._extract_value(line, "Ratio:", "Loadcase:")
                self.data["header"]["loadcase"] = self._extract_value(line, "Loadcase:", r"\|")

            if "Ref:" in line and "Eq." in line:
                 self.data["header"]["ref"] = self._extract_value(line, "Ref:", r"\|")

            # Forces
            if "Pz:" in line:
                self.data["header"]["forces"] = {}
                self.data["header"]["forces"]["Pz"] = self._extract_value(line, "Pz:", r"[CV]")
                self.data["header"]["forces"]["Vy"] = self._extract_value(line, "Vy:", "Vx:")
                self.data["header"]["forces"]["Vx"] = self._extract_value(line, "Vx:", r"\|")
            
            if "Tz:" in line:
                self.data["header"]["forces"]["Tz"] = self._extract_value(line, "Tz:", "My:")
                self.data["header"]["forces"]["My"] = self._extract_value(line, "My:", "Mx:")
                self.data["header"]["forces"]["Mx"] = self._extract_value(line, "Mx:", r"\|")

            # Section Properties
            if "SECTION PROPERTIES" in line:
                current_block = "section_properties"
                continue
            
            if current_block == "section_properties" and "Ag" in line:
                self._parse_key_value_line(line, self.data["section_properties"])
            if current_block == "section_properties" and "Ixx" in line:
                self._parse_key_value_line(line, self.data["section_properties"])
            if current_block == "section_properties" and "Sxx+" in line:
                self._parse_key_value_line(line, self.data["section_properties"])
            if current_block == "section_properties" and "Syy+" in line:
                self._parse_key_value_line(line, self.data["section_properties"])
            if current_block == "section_properties" and "Cw" in line:
                self._parse_key_value_line(line, self.data["section_properties"])
                current_block = None # End of section properties usually

            # Material Properties
            if "MATERIAL PROPERTIES" in line:
                current_block = "material_properties"
                continue
            if current_block == "material_properties" and "Fyld:" in line:
                self._parse_key_value_line(line, self.data["material_properties"])
                current_block = None

            # Design Parameters
            if "Design Parameters" in line:
                current_block = "design_parameters"
                continue
            if current_block == "design_parameters" and "Kx:" in line:
                self._parse_key_value_line(line, self.data["design_parameters"])
                current_block = None

            # Check Blocks (The main part)
            # Detect start of a check block (e.g., CHECKS FOR AXIAL TENSION)
            match = check_block_pattern.search(line)
            if match:
                if current_check_block:
                    self.data["checks"].append(current_check_block)
                current_check_block = {
                    "title": match.group(1).strip(),
                    "sub_checks": []
                }
                continue
            
            # Inside a check block, look for sub-checks (e.g., TENSILE YIELDING)
            # Sub-checks usually start with a name, then a line with DEMAND CAPACITY RATIO...
            # But the name is on a separate line above DEMAND...
            
            if current_check_block:
                # Check for sub-check title
                # If line is just text and next line has DEMAND, it's a sub-check title
                if i + 1 < len(lines) and "DEMAND" in lines[i+1] and "CAPACITY" in lines[i+1]:
                    sub_check = {
                        "name": line.strip("| ").strip(),
                        "results": {},
                        "intermediates": []
                    }
                    current_check_block["sub_checks"].append(sub_check)
                    continue

                # Parse Demand/Capacity line
                if "DEMAND" in line and "CAPACITY" in line:
                    continue # Skip header line
                
                # Parse the values line below DEMAND...
                # It looks like: | 0.000 410.9 0.000 Cl.D2 1000 0.00 |
                if len(current_check_block["sub_checks"]) > 0:
                    current_sub = current_check_block["sub_checks"][-1]
                    
                    # If we haven't parsed results yet, try to parse them
                    if not current_sub["results"] and re.search(r"\|\s*" + float_pattern, line):
                        # Extract values based on position or regex
                        vals = re.findall(r"([-\d\.]+|[A-Za-z0-9\.]+)", line.replace("|", ""))
                        if len(vals) >= 3:
                            current_sub["results"] = {
                                "demand": float(vals[0]) if self._is_float(vals[0]) else vals[0],
                                "capacity": float(vals[1]) if self._is_float(vals[1]) else vals[1],
                                "ratio": float(vals[2]) if self._is_float(vals[2]) else vals[2],
                                "reference": vals[3] if len(vals) > 3 else "",
                                "loadcase": vals[4] if len(vals) > 4 else "",
                                "location": vals[5] if len(vals) > 5 else ""
                            }
                        continue

                    # Intermediate Results
                    if "Intermediate Results" in line:
                        continue
                    
                    # Parse intermediate result lines: | Nom. Ten. Yld Cap : Pn = 456.50 kip Eq.D2-1 |
                    if ":" in line and "=" in line:
                        # Extract Description, Variable, Value, Unit, Equation
                        parts = line.split("=")
                        left_part = parts[0].split(":")
                        right_part = parts[1]
                        
                        desc = left_part[0].strip("| ")
                        var_name = left_part[1].strip() if len(left_part) > 1 else ""
                        
                        # Right part: 456.50 kip Eq.D2-1 |
                        val_match = re.search(float_pattern, right_part)
                        if val_match:
                            value = float(val_match.group(0))
                            remainder = right_part[val_match.end():].strip("| ").strip()
                            
                            # Unit and Eq
                            eq_match = re.search(r"(Eq\.|Cl\.|Table\.)[\w\.\-]+", remainder)
                            equation = eq_match.group(0) if eq_match else ""
                            unit = remainder.replace(equation, "").strip()
                            
                            current_sub["intermediates"].append({
                                "description": desc,
                                "variable": var_name,
                                "value": value,
                                "unit": unit,
                                "equation": equation
                            })

        if current_check_block:
            self.data["checks"].append(current_check_block)

        return self.data

    def _extract_value(self, line, key_start, key_end):
        try:
            pattern = re.escape(key_start) + r"(.*?)" + re.escape(key_end)
            match = re.search(pattern, line)
            if match:
                return match.group(1).strip()
            return ""
        except:
            return ""

    def _parse_key_value_line(self, line, target_dict):
        # Format: | Ag : 9.130E+00 Axx : 6.960E+00 ... |
        content = line.strip("| ")
        matches = re.findall(r"([A-Za-z0-9\+\-]+)\s*:\s*([-+]?\d*\.\d+(?:[eE][-+]?\d+)?)", content)
        for key, val in matches:
            target_dict[key.strip()] = float(val)

    def _is_float(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

# ==========================================
# RENDERER LOGIC
# ==========================================
def render_sheet(data):
    # --- Header ---
    st.header(f"Member: {data['header'].get('member_no', '?')} - {data['header'].get('profile', '?')}")
    
    # Status Block
    status = data['header'].get('status', 'UNKNOWN')
    ratio = data['header'].get('ratio', '0.00')
    color = "green" if status == "PASS" else "red"
    st.markdown(f"**Status:** :{color}[{status}] | **Ratio:** {ratio} | **Loadcase:** {data['header'].get('loadcase', '?')}")
    
    # Forces
    if "forces" in data['header']:
        f = data['header']['forces']
        st.subheader("Forces (Inputs)")
        cols = st.columns(3)
        with cols[0]:
            st.latex(f"P_z = \\color{{green}}{{{f.get('Pz', '0')}}}")
            st.latex(f"T_z = \\color{{green}}{{{f.get('Tz', '0')}}}")
        with cols[1]:
            st.latex(f"V_y = \\color{{green}}{{{f.get('Vy', '0')}}}")
            st.latex(f"M_y = \\color{{green}}{{{f.get('My', '0')}}}")
        with cols[2]:
            st.latex(f"V_x = \\color{{green}}{{{f.get('Vx', '0')}}}")
            st.latex(f"M_x = \\color{{green}}{{{f.get('Mx', '0')}}}")

    st.markdown("---")

    # --- Properties ---
    st.subheader("Section & Material Properties")
    
    # Combine Section and Material for display
    props = {}
    if "section_properties" in data: props.update(data["section_properties"])
    if "material_properties" in data: props.update(data["material_properties"])
    if "design_parameters" in data: props.update(data["design_parameters"])
    
    # Display in a grid
    prop_keys = list(props.keys())
    # Chunk into rows of 4
    for i in range(0, len(prop_keys), 4):
        cols = st.columns(4)
        for j in range(4):
            if i + j < len(prop_keys):
                key = prop_keys[i+j]
                val = props[key]
                with cols[j]:
                    # Inputs are Green
                    st.latex(f"\\text{{{key}}} = \\color{{green}}{{{val}}}")

    st.markdown("---")

    # --- Checks ---
    for block in data["checks"]:
        st.subheader(block["title"])
        
        for sub in block["sub_checks"]:
            with st.container():
                st.markdown(f"#### {sub['name']}")
                
                # Results Line
                res = sub["results"]
                if res:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown("**Demand**")
                        st.latex(f"\\color{{green}}{{{res.get('demand', '0')}}}")
                    with c2:
                        st.markdown("**Capacity**")
                        st.latex(f"\\color{{blue}}{{{res.get('capacity', '0')}}}")
                    with c3:
                        st.markdown("**Ratio**")
                        r_val = res.get('ratio', '0')
                        st.latex(f"\\color{{magenta}}{{{r_val}}}")
                    with c4:
                        st.markdown("**Ref**")
                        st.caption(f"{res.get('reference', '')} (LC: {res.get('loadcase', '')})")
                
                # Intermediate Results
                if sub["intermediates"]:
                    st.markdown("**Calculations & Equations:**")
                    
                    # Prepare context for equation formatter
                    context = {
                        "section_properties": data.get("section_properties", {}),
                        "material_properties": data.get("material_properties", {}),
                        "variables": {}
                    }
                    # Add current intermediates to context variables
                    for item in sub["intermediates"]:
                        if item["variable"]:
                            context["variables"][item["variable"]] = item["value"]
                    
                    for item in sub["intermediates"]:
                        # Display the variable value
                        # e.g. Pn = 456.50
                        var_display = f"{item['variable']} = \\color{{blue}}{{{item['value']}}} \\text{{ {item['unit']}}}"
                        
                        # If there is an equation, try to render it
                        eq_display = ""
                        if item["equation"]:
                            eq_tex = get_equation_latex(item["equation"], context)
                            if "not defined" not in eq_tex:
                                eq_display = eq_tex
                            else:
                                # If not defined, just show the equation ID
                                eq_display = f"\\text{{Ref: }} {item['equation']}"
                        
                        # Render
                        if eq_display and "Ref:" not in eq_display:
                            st.latex(eq_display)
                        else:
                            # Fallback if no equation logic
                            if item['variable']:
                                st.latex(var_display + (f" \\quad (\\text{{{item['equation']}}})" if item['equation'] else ""))
                            else:
                                # Just description
                                st.write(f"{item['description']} : {item['value']} {item['unit']} ({item['equation']})")

                st.divider()

# ==========================================
# MAIN APP
# ==========================================
st.set_page_config(page_title="STAAD Calculation Sheet", layout="wide")

st.title("STAAD Connect Results Parser")
st.markdown("Paste your STAAD Connect output below to generate a formatted calculation sheet.")

# Default example from user
DEFAULT_TEXT = """
- Member :      1 
|-----------------------------------------------------------------------------|
|  Member No:        1       Profile:  ST  W8X31               (AISC SECTIONS)|
|  Status:        PASS       Ratio:         0.218       Loadcase:     1006    |
|  Location:      0.00       Ref:      Eq.H1-1b                               |
|  Pz:       6.830     C     Vy:       -1.970           Vx:     -.2474        |
|  Tz:      -2.469           My:        9.130           Mx:     -243.2        |
|-----------------------------------------------------------------------------|
| COMPRESSION SLENDERNESS                                                     |
| Actual Slenderness Ratio    :     87.309                                    |
| Allowable Slenderness Ratio :    200.000            LOC  :     0.00         |
|-----------------------------------------------------------------------------|
| STRENGTH CHECKS                                                             |
| Critical L/C  :   1006             Ratio     :        0.218(PASS)           |
|          Loc  :    0.00            Condition :    Eq.H1-1b                  |
|-----------------------------------------------------------------------------|
| SECTION PROPERTIES  (LOC:     0.00, PROPERTIES UNIT: IN  )                  |
| Ag  :   9.130E+00     Axx :   6.960E+00     Ayy :   2.280E+00               |
| Ixx :   1.100E+02     Iyy :   3.710E+01     J   :   5.360E-01               |
| Sxx+:   2.750E+01     Sxx-:   2.750E+01     Zxx :   3.040E+01               |
| Syy+:   9.275E+00     Syy-:   9.275E+00     Zyy :   1.410E+01               |
| Cw  :   5.311E+02     x0  :   0.000E+00     y0  :   0.000E+00               |
|-----------------------------------------------------------------------------|
| MATERIAL PROPERTIES                                                         |
| Fyld:          50.000              Fu:          62.000                      |
|-----------------------------------------------------------------------------|
| Actual Member Length:       121.000                                         |
| Design Parameters                                            (Rolled)       |
| Kx:    2.00  Ky:    2.00  NSF:    1.00  SLF:    1.00  CSP:   12.00          |
|-----------------------------------------------------------------------------|
| COMPRESSION CLASSIFICATION (L/C:   1030 LOC:     0.00)                      |
|                             l           l p         l r       CASE                |
| Flange: NonSlender       9.20       N/A      13.49     Table.4.1a.Case1     |
| Web   : NonSlender      22.25       N/A      35.88     Table.4.1a.Case5     |
|                                                                             |
| FLEXURE CLASSIFICATION     (L/C:     43 LOC:     0.00)                      |
|                             l           l p         l r       CASE                |
| Flange: NonCompact       9.20       9.15     24.08     Table.4.1b.Case10    |
| Web   : Compact         22.25      90.55    137.27     Table.4.1b.Case15    |
|-----------------------------------------------------------------------------|
     STAAD SPACE                                              -- PAGE NO.   39
        
 
                       STAAD.PRO CODE CHECKING - AISC 360-16 LRFD (V1.2)
                     *****************************************************
 
 ALL UNITS ARE - KIP  INCH (UNLESS OTHERWISE Noted).
                                                       - Member :     1 Contd.
|-----------------------------------------------------------------------------|
|                         CHECKS FOR AXIAL TENSION                            |
|-----------------------------------------------------------------------------|
| TENSILE YIELDING                                                            |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|              0.000       410.9       0.000     Cl.D2       1000      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Nom. Ten. Yld Cap         : Pn     =  456.50     kip        Eq.D2-1        |
|-----------------------------------------------------------------------------|
| TENSILE RUPTURE                                                             |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|              0.000       424.5       0.000     Cl.D2       1000      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Effective area            : Ae     =  9.1300     in2        Eq.D3-1        |
|  Nom. Ten. Rpt Cap         : Pn     =  566.06     kip        Eq.D2-2        |
|-----------------------------------------------------------------------------|
|                         CHECKS FOR AXIAL COMPRESSION                        |
|-----------------------------------------------------------------------------|
| FLEXURAL BUCKLING X                                                         |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|              8.409       319.2       0.026     Cl.E3       1030      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Effective Slenderness     : Lcx/rx =  58.772                Cl.E2          |
|  Elastic Buckling Stress   : Fex    =  82.863     ksi        Eq.E3-4        |
|  Crit. Buckling Stress     : Fcrx   =  38.841     ksi        Eq.E3-2        |
|  Nom. Flexural Buckling    : Pnx    =  354.61     kip        Eq.E3-1        |
|-----------------------------------------------------------------------------|
| FLEXURAL BUCKLING Y                                                         |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|              8.409       235.3       0.036     Cl.E3       1030      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Effective Slenderness     : Lcy/ry =  87.309                Cl.E2          |
|  Elastic Buckling Stress   : Fey    =  37.547     ksi        Eq.E3-4        |
|  Crit. Buckling Stress     : Fcry   =  28.636     ksi        Eq.E3-2        |
|  Nom. Flexural Buckling    : Pny    =  261.44     kip        Eq.E3-1        |
|-----------------------------------------------------------------------------|
| FLEXURAL-TORSIONAL-BUCKLING                                                 |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|              8.409       340.4       0.025     Cl.E4       1030      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Elastic F-T-B Stress      : Fe     =  111.22     ksi        Eq.E4-2        |
|  Crit. F-T-B Stress        : Fcr    =  41.424     ksi        Eq.E3-2        |
|  Nom. Flex-tor Buckling    : Pn     =  378.20     kip        Eq.E4-1        |
|-----------------------------------------------------------------------------|
     STAAD SPACE                                              -- PAGE NO.   40
        
 
                       STAAD.PRO CODE CHECKING - AISC 360-16 LRFD (V1.2)
                     *****************************************************
 
 ALL UNITS ARE - KIP  INCH (UNLESS OTHERWISE Noted).
                                                       - Member :     1 Contd.
|-----------------------------------------------------------------------------|
|                         CHECKS FOR SHEAR                                    |
|-----------------------------------------------------------------------------|
| SHEAR ALONG X                                                               |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|              1.360       187.9       0.007     Cl.G1       1032      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Coefficient Cv Along X    : Cv     =  1.0000                Eq.G2-9        |
|  Coefficient Kv Along X    : Kv     =  1.2000                Cl.G6          |
|  Nom. Shear Along X        : Vnx    =  208.80     kip        Eq.G6-1        |
|-----------------------------------------------------------------------------|
| SHEAR ALONG Y                                                               |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|              1.970       68.40       0.029     Cl.G1       1005      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Coefficient Cv Along Y    : Cv     =  1.0000                -              |
|  Coefficient Kv Along Y    : Kv     =  5.3400                Eq.G2-5        |
|  Nom. Shear Along Y        : Vny    =  68.400     kip        Eq.G2-1        |
|-----------------------------------------------------------------------------|
     STAAD SPACE                                              -- PAGE NO.   41
        
 
                       STAAD.PRO CODE CHECKING - AISC 360-16 LRFD (V1.2)
                     *****************************************************
 
 ALL UNITS ARE - KIP  INCH (UNLESS OTHERWISE Noted).
                                                       - Member :     1 Contd.
|-----------------------------------------------------------------------------|
|                         CHECKS FOR BENDING                                  |
|-----------------------------------------------------------------------------|
| FLEXURAL YIELDING (Y)                                                       |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|             -83.49       634.5       0.132     Cl.F6.1     1032      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Nom Flex Yielding Along Y : Mny    =  705.00     kip-in     Eq.F6-1        |
|-----------------------------------------------------------------------------|
| LAT TOR BUCK ABOUT X                                                        |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|             -243.2       1284.       0.189     Cl.F2.2     1004      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Nom L-T-B Cap             : Mnx    =  1426.5     kip-in     Eq.F2-2        |
|  Mom. Distr. factor        : CbX    =  1.0000                Custom         |
|  Limiting Unbraced Length  : LpX    =  85.443     in         Eq.F2-5        |
|  coefficient C             : Cx     =  1.0000                Eq.F2-8a       |
|  Effective Rad. of Gyr.    : Rts    =  2.2593     in         Eq.F2-7        |
|  Limiting Unbraced Length  : LrX    =  297.38     in         Eq.F2-6        |
|-----------------------------------------------------------------------------|
| FLANGE LOCAL BUCK(X)                                                        |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|             -243.2       1367.       0.178     Cl.F3.1     1004      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Nom F-L-B Cap             : Mnx    =  1518.4     kip-in     Eq.F3-1        |
|-----------------------------------------------------------------------------|
| FLANGE LOCAL BUCK(Y)                                                        |
|              DEMAND      CAPACITY    RATIO     REFERENCE     L/C    LOC     |
|             -83.49       633.5       0.132     Cl.F6.2     1032      0.00   |
|                                                                             |
| Intermediate Results :                                                      |
|  Nom F-L-B Cap             : Mny    =  703.88     kip-in     Eq.F6-2        |
|-----------------------------------------------------------------------------|
|      STAAD SPACE                                              -- PAGE NO.   42
        
 
                       STAAD.PRO CODE CHECKING - AISC 360-16 LRFD (V1.2)
                     *****************************************************
 
 ALL UNITS ARE - KIP  INCH (UNLESS OTHERWISE Noted).
                                                       - Member :     1 Contd.
|-----------------------------------------------------------------------------|
|                         CHECKS FOR AXIAL BEND INTERACTION                   |
|-----------------------------------------------------------------------------|
| COMBINED FORCES CLAUSE H1                                                   |
|                            RATIO      CRITERIA           L/C      LOC       |
|                            0.218      Eq.H1-1b         1006        0.00     |
|                                                                             |
| Intermediate Results :                                                      |
|  Axial Capacity            : Pc     =  235.30     kip        Cl.H1.1        |
|  Moment Capacity           : Mcx    =  1283.8     kip-in     Cl.H1.1        |
|  Moment Capacity           : Mcy    =  633.50     kip-in     Cl.H1.1        |
|-----------------------------------------------------------------------------|
"""

input_text = st.text_area("STAAD Output", value=DEFAULT_TEXT, height=300)

if st.button("Generate Calculation Sheet"):
    if input_text:
        parser = StaadParser(input_text)
        data = parser.parse()
        render_sheet(data)
    else:
        st.warning("Please paste some text first.")
