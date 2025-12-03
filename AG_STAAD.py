
import streamlit as st
import pandas as pd
import re

# ==========================================
# 1. PARSING LOGIC
# ==========================================
def parse_value(line, key):
    """Helper to extract a float value after a key in a line."""
    # Look for key followed by : or = and then a number (possibly scientific)
    # We handle cases like "Pz: 6.830" or "Ag : 9.130E+00"
    match = re.search(rf"{key}\s*[:=]\s*([-\d.E+]+)", line)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    return 0.0

def parse_staad_report(text):
    data = {
        "id": "Unknown", "profile": "Unknown", "status": "Unknown", "ratio": 0.0, "loadcase": "Unknown",
        "forces": {}, "properties": {}, "material": {}, "params": {}, "checks": {}
    }
    
    lines = text.split('\n')
    
    # Initialize checks structure with defaults
    checks = {
        "tension_yielding": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Pn": 0, "eqn": ""},
        "tension_rupture": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Ae": 0, "Pn": 0, "eqn": ""},
        "compression_x": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Lcx_rx": 0, "Fex": 0, "Fcrx": 0, "Pnx": 0},
        "compression_y": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Lcy_ry": 0, "Fey": 0, "Fcry": 0, "Pny": 0},
        "ftb": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Fe": 0, "Fcr": 0, "Pn": 0},
        "shear_x": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Cv": 0, "Vnx": 0},
        "shear_y": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Cv": 0, "Vny": 0},
        "ltb_x": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Mnx": 0, "Cb": 1.0, "Lp": 0, "Lr": 0, "Rts": 0},
        "flb_x": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Mnx": 0},
        "flb_y": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Mny": 0},
        "flexure_y": {"demand": 0, "capacity": 0, "ratio": 0, "ref": "", "Mny": 0},
        "interaction": {"ratio": 0, "criteria": "", "Pc": 0, "Mcx": 0, "Mcy": 0}
    }

    # Initialize classification structure
    classification = {
        "compression": {
            "flange": {"status": "", "lambda": 0, "lambda_p": "N/A", "lambda_r": 0, "case": ""},
            "web": {"status": "", "lambda": 0, "lambda_p": "N/A", "lambda_r": 0, "case": ""}
        },
        "flexure": {
            "flange": {"status": "", "lambda": 0, "lambda_p": 0, "lambda_r": 0, "case": ""},
            "web": {"status": "", "lambda": 0, "lambda_p": 0, "lambda_r": 0, "case": ""}
        }
    }
    data["classification"] = classification
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line: continue

        # General Info
        if "Member No:" in line:
            m = re.search(r"Member No:\s+(\d+)", line)
            if m: data["id"] = m.group(1)
            m = re.search(r"Profile:\s+(.*?)\s+\(", line)
            if m: data["profile"] = m.group(1).strip()
            
        if "Status:" in line:
            m = re.search(r"Status:\s+(\w+)", line)
            if m: data["status"] = m.group(1)
            val = parse_value(line, "Ratio")
            if val: data["ratio"] = val
            m = re.search(r"Loadcase:\s+(\d+)", line)
            if m: data["loadcase"] = m.group(1)
            
        # Forces
        if "Pz:" in line:
            data["forces"]["Pz"] = {"value": parse_value(line, "Pz"), "unit": "kips", "desc": "Axial Compression"}
            data["forces"]["Vy"] = {"value": parse_value(line, "Vy"), "unit": "kips", "desc": "Shear Y"}
            data["forces"]["Vx"] = {"value": parse_value(line, "Vx"), "unit": "kips", "desc": "Shear X"}
        if "Tz:" in line:
            data["forces"]["Tz"] = {"value": parse_value(line, "Tz"), "unit": "kip-in", "desc": "Torsion"}
            data["forces"]["My"] = {"value": parse_value(line, "My"), "unit": "kip-in", "desc": "Moment Y"}
            data["forces"]["Mx"] = {"value": parse_value(line, "Mx"), "unit": "kip-in", "desc": "Moment X"}
            
        # Properties
        if "Ag  :" in line:
            data["properties"]["Ag"] = {"value": parse_value(line, "Ag"), "unit": "in²"}
            data["properties"]["Axx"] = {"value": parse_value(line, "Axx"), "unit": "in²"}
            data["properties"]["Ayy"] = {"value": parse_value(line, "Ayy"), "unit": "in²"}
        if "Ixx :" in line:
            data["properties"]["Ixx"] = {"value": parse_value(line, "Ixx"), "unit": "in⁴"}
            data["properties"]["Iyy"] = {"value": parse_value(line, "Iyy"), "unit": "in⁴"}
            data["properties"]["J"] = {"value": parse_value(line, "J"), "unit": "in⁴"}
        if "Sxx+:" in line:
            # Escape + for regex
            data["properties"]["Sxx"] = {"value": parse_value(line, r"Sxx\+"), "unit": "in³"} 
            data["properties"]["Zxx"] = {"value": parse_value(line, "Zxx"), "unit": "in³"}
        if "Syy+:" in line:
            data["properties"]["Syy"] = {"value": parse_value(line, r"Syy\+"), "unit": "in³"}
            data["properties"]["Zyy"] = {"value": parse_value(line, "Zyy"), "unit": "in³"}
        if "Cw  :" in line:
            data["properties"]["Cw"] = {"value": parse_value(line, "Cw"), "unit": "in⁶"}
            
        # Material
        if "Fyld:" in line:
            data["material"]["Fyld"] = parse_value(line, "Fyld")
            data["material"]["Fu"] = parse_value(line, "Fu")
            
        # Parameters
        if "Actual Member Length:" in line:
            data["params"]["Length"] = parse_value(line, "Actual Member Length")
        if "Kx:" in line:
            data["params"]["Kx"] = parse_value(line, "Kx")
            data["params"]["Ky"] = parse_value(line, "Ky")
            
        # Section Detection
        if "TENSILE YIELDING" in line: current_section = "tens_yield"
        elif "TENSILE RUPTURE" in line: current_section = "tens_rup"
        elif "FLEXURAL BUCKLING X" in line: current_section = "comp_x"
        elif "FLEXURAL BUCKLING Y" in line: current_section = "comp_y"
        elif "FLEXURAL-TORSIONAL-BUCKLING" in line: current_section = "ftb"
        elif "SHEAR ALONG X" in line: current_section = "shear_x"
        elif "SHEAR ALONG Y" in line: current_section = "shear_y"
        elif "FLEXURAL YIELDING (Y)" in line: current_section = "flex_y"
        elif "LAT TOR BUCK ABOUT X" in line: current_section = "ltb_x"
        elif "FLANGE LOCAL BUCK(X)" in line: current_section = "flb_x"
        elif "FLANGE LOCAL BUCK(Y)" in line: current_section = "flb_y"
        elif "COMBINED FORCES CLAUSE H1" in line: current_section = "inter"
        elif "COMPRESSION CLASSIFICATION" in line: current_section = "class_comp"
        elif "FLEXURE CLASSIFICATION" in line: current_section = "class_flex"

        # Parsing based on section
        # We look for lines that contain specific keywords or patterns
        
        if current_section == "tens_yield":
            if "Cl.D" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["tension_yielding"]["demand"] = float(vals[0])
                     checks["tension_yielding"]["capacity"] = float(vals[1])
                     checks["tension_yielding"]["ratio"] = float(vals[2])
                     checks["tension_yielding"]["ref"] = "Cl.D2"
            if "Nom. Ten. Yld Cap" in line:
                checks["tension_yielding"]["Pn"] = parse_value(line, "Pn")
                m = re.search(r"(Eq\.[-\w]+)", line)
                if m: checks["tension_yielding"]["eqn"] = m.group(1)

        elif current_section == "tens_rup":
            if "Cl.D" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["tension_rupture"]["demand"] = float(vals[0])
                     checks["tension_rupture"]["capacity"] = float(vals[1])
                     checks["tension_rupture"]["ratio"] = float(vals[2])
                     checks["tension_rupture"]["ref"] = "Cl.D2"
            if "Effective area" in line: checks["tension_rupture"]["Ae"] = parse_value(line, "Ae")
            if "Nom. Ten. Rpt Cap" in line: 
                checks["tension_rupture"]["Pn"] = parse_value(line, "Pn")
                m = re.search(r"(Eq\.[-\w]+)", line)
                if m: checks["tension_rupture"]["eqn"] = m.group(1)

        elif current_section == "comp_x":
            if "Cl.E" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["compression_x"]["demand"] = float(vals[0])
                     checks["compression_x"]["capacity"] = float(vals[1])
                     checks["compression_x"]["ratio"] = float(vals[2])
                     checks["compression_x"]["ref"] = "Cl.E3"
            if "Effective Slenderness" in line: checks["compression_x"]["Lcx_rx"] = parse_value(line, "Lcx/rx")
            if "Elastic Buckling Stress" in line: checks["compression_x"]["Fex"] = parse_value(line, "Fex")
            if "Crit. Buckling Stress" in line: checks["compression_x"]["Fcrx"] = parse_value(line, "Fcrx")
            if "Nom. Flexural Buckling" in line: checks["compression_x"]["Pnx"] = parse_value(line, "Pnx")

        elif current_section == "comp_y":
            if "Cl.E" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["compression_y"]["demand"] = float(vals[0])
                     checks["compression_y"]["capacity"] = float(vals[1])
                     checks["compression_y"]["ratio"] = float(vals[2])
                     checks["compression_y"]["ref"] = "Cl.E3"
            if "Effective Slenderness" in line: checks["compression_y"]["Lcy_ry"] = parse_value(line, "Lcy/ry")
            if "Elastic Buckling Stress" in line: checks["compression_y"]["Fey"] = parse_value(line, "Fey")
            if "Crit. Buckling Stress" in line: checks["compression_y"]["Fcry"] = parse_value(line, "Fcry")
            if "Nom. Flexural Buckling" in line: checks["compression_y"]["Pny"] = parse_value(line, "Pny")

        elif current_section == "ftb":
            if "Cl.E" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["ftb"]["demand"] = float(vals[0])
                     checks["ftb"]["capacity"] = float(vals[1])
                     checks["ftb"]["ratio"] = float(vals[2])
                     checks["ftb"]["ref"] = "Cl.E4"
            if "Elastic F-T-B Stress" in line: checks["ftb"]["Fe"] = parse_value(line, "Fe")
            if "Crit. F-T-B Stress" in line: checks["ftb"]["Fcr"] = parse_value(line, "Fcr")
            if "Nom. Flex-tor Buckling" in line: checks["ftb"]["Pn"] = parse_value(line, "Pn")

        elif current_section == "shear_x":
            if "Cl.G" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["shear_x"]["demand"] = float(vals[0])
                     checks["shear_x"]["capacity"] = float(vals[1])
                     checks["shear_x"]["ratio"] = float(vals[2])
                     checks["shear_x"]["ref"] = "Cl.G1"
            if "Coefficient Cv" in line: checks["shear_x"]["Cv"] = parse_value(line, "Cv")
            if "Nom. Shear Along X" in line: checks["shear_x"]["Vnx"] = parse_value(line, "Vnx")

        elif current_section == "shear_y":
            if "Cl.G" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["shear_y"]["demand"] = float(vals[0])
                     checks["shear_y"]["capacity"] = float(vals[1])
                     checks["shear_y"]["ratio"] = float(vals[2])
                     checks["shear_y"]["ref"] = "Cl.G1"
            if "Coefficient Cv" in line: checks["shear_y"]["Cv"] = parse_value(line, "Cv")
            if "Nom. Shear Along Y" in line: checks["shear_y"]["Vny"] = parse_value(line, "Vny")

        elif current_section == "flex_y":
            if "Cl.F" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["flexure_y"]["demand"] = float(vals[0])
                     checks["flexure_y"]["capacity"] = float(vals[1])
                     checks["flexure_y"]["ratio"] = float(vals[2])
                     checks["flexure_y"]["ref"] = "Cl.F6.1"
            if "Nom Flex Yielding" in line: checks["flexure_y"]["Mny"] = parse_value(line, "Mny")

        elif current_section == "ltb_x":
            if "Cl.F" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["ltb_x"]["demand"] = float(vals[0])
                     checks["ltb_x"]["capacity"] = float(vals[1])
                     checks["ltb_x"]["ratio"] = float(vals[2])
                     checks["ltb_x"]["ref"] = "Cl.F2.2"
            if "Nom L-T-B Cap" in line: checks["ltb_x"]["Mnx"] = parse_value(line, "Mnx")
            if "Mom. Distr. factor" in line: checks["ltb_x"]["Cb"] = parse_value(line, "CbX")
            if "Limiting Unbraced Length" in line and "LpX" in line: checks["ltb_x"]["Lp"] = parse_value(line, "LpX")
            if "Limiting Unbraced Length" in line and "LrX" in line: checks["ltb_x"]["Lr"] = parse_value(line, "LrX")
            if "Effective Rad. of Gyr." in line: checks["ltb_x"]["Rts"] = parse_value(line, "Rts")

        elif current_section == "flb_x":
            if "Cl.F" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["flb_x"]["demand"] = float(vals[0])
                     checks["flb_x"]["capacity"] = float(vals[1])
                     checks["flb_x"]["ratio"] = float(vals[2])
                     checks["flb_x"]["ref"] = "Cl.F3.1"
            if "Nom F-L-B Cap" in line: checks["flb_x"]["Mnx"] = parse_value(line, "Mnx")

        elif current_section == "flb_y":
            if "Cl.F" in line and "DEMAND" not in line:
                 vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                 if len(vals) >= 3:
                     checks["flb_y"]["demand"] = float(vals[0])
                     checks["flb_y"]["capacity"] = float(vals[1])
                     checks["flb_y"]["ratio"] = float(vals[2])
                     checks["flb_y"]["ref"] = "Cl.F6.2"
            if "Nom F-L-B Cap" in line: checks["flb_y"]["Mny"] = parse_value(line, "Mny")

        elif current_section == "inter":
            if "Eq.H1" in line and "RATIO" not in line:
                # 0.218 Eq.H1-1b 1006 0.00
                vals = re.findall(r"[-+]?\d*\.\d+|\d+", line)
                if len(vals) >= 1:
                    checks["interaction"]["ratio"] = float(vals[0])
                m = re.search(r"(Eq\.H1[-\w]+)", line)
                if m: checks["interaction"]["criteria"] = m.group(1)
            if "Axial Capacity" in line: checks["interaction"]["Pc"] = parse_value(line, "Pc")
            if "Moment Capacity" in line and "Mcx" in line: checks["interaction"]["Mcx"] = parse_value(line, "Mcx")
            if "Moment Capacity" in line and "Mcy" in line: checks["interaction"]["Mcy"] = parse_value(line, "Mcy")

        elif current_section == "class_comp":
            # Flange: NonSlender       9.20       N/A      13.49     Table.4.1a.Case1
            if "Flange:" in line:
                m = re.search(r"Flange:\s+(\w+)\s+([\d.]+)\s+(N/A|[\d.]+)\s+(N/A|[\d.]+)\s+([\w.]+)", line)
                if m:
                    data["classification"]["compression"]["flange"] = {
                        "status": m.group(1), "lambda": float(m.group(2)), 
                        "lambda_p": m.group(3), "lambda_r": float(m.group(4)) if m.group(4) != "N/A" else "N/A",
                        "case": m.group(5)
                    }
            if "Web   :" in line:
                m = re.search(r"Web\s+:\s+(\w+)\s+([\d.]+)\s+(N/A|[\d.]+)\s+(N/A|[\d.]+)\s+([\w.]+)", line)
                if m:
                    data["classification"]["compression"]["web"] = {
                        "status": m.group(1), "lambda": float(m.group(2)), 
                        "lambda_p": m.group(3), "lambda_r": float(m.group(4)) if m.group(4) != "N/A" else "N/A",
                        "case": m.group(5)
                    }

        elif current_section == "class_flex":
            # Flange: NonCompact       9.20       9.15     24.08     Table.4.1b.Case10
            if "Flange:" in line:
                m = re.search(r"Flange:\s+(\w+)\s+([\d.]+)\s+(N/A|[\d.]+)\s+(N/A|[\d.]+)\s+([\w.]+)", line)
                if m:
                    data["classification"]["flexure"]["flange"] = {
                        "status": m.group(1), "lambda": float(m.group(2)), 
                        "lambda_p": float(m.group(3)) if m.group(3) != "N/A" else "N/A", 
                        "lambda_r": float(m.group(4)) if m.group(4) != "N/A" else "N/A",
                        "case": m.group(5)
                    }
            if "Web   :" in line:
                m = re.search(r"Web\s+:\s+(\w+)\s+([\d.]+)\s+(N/A|[\d.]+)\s+(N/A|[\d.]+)\s+([\w.]+)", line)
                if m:
                    data["classification"]["flexure"]["web"] = {
                        "status": m.group(1), "lambda": float(m.group(2)), 
                        "lambda_p": float(m.group(3)) if m.group(3) != "N/A" else "N/A", 
                        "lambda_r": float(m.group(4)) if m.group(4) != "N/A" else "N/A",
                        "case": m.group(5)
                    }

    # Fallback for Cb if not found in LTB section (sometimes in params)
    if checks["ltb_x"]["Cb"] == 1.0 and "Cb" in data["params"]:
        pass
    else:
        data["params"]["Cb"] = checks["ltb_x"]["Cb"]

    data["checks"] = checks
    return data

# ==========================================
# 2. DEFAULT DATA (Fallback)
# ==========================================
default_member_data = {
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
    "classification": {
        "compression": {
            "flange": {"status": "NonSlender", "lambda": 9.20, "lambda_p": "N/A", "lambda_r": 13.49, "case": "Table.4.1a.Case1"},
            "web": {"status": "NonSlender", "lambda": 22.25, "lambda_p": "N/A", "lambda_r": 35.88, "case": "Table.4.1a.Case5"}
        },
        "flexure": {
            "flange": {"status": "NonCompact", "lambda": 9.20, "lambda_p": 9.15, "lambda_r": 24.08, "case": "Table.4.1b.Case10"},
            "web": {"status": "Compact", "lambda": 22.25, "lambda_p": 90.55, "lambda_r": 137.27, "case": "Table.4.1b.Case15"}
        }
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
        "ftb": {
             "demand": 8.409, "capacity": 340.4, "ratio": 0.025, "ref": "Cl.E4",
             "Fe": 111.22, "Fcr": 41.424, "Pn": 378.20
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
            "Mnx": 1426.5, "Cb": 1.000, "Lp": 85.443, "Lr": 297.38, "Rts": 2.2593
        },
        "flb_x": {
            "demand": -243.2, "capacity": 1367.0, "ratio": 0.178, "ref": "Cl.F3.1",
            "Mnx": 1518.4
        },
        "flb_y": {
            "demand": -83.49, "capacity": 633.5, "ratio": 0.132, "ref": "Cl.F6.2",
            "Mny": 703.88
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
# 3. HELPER FUNCTIONS
# ==========================================
def render_latex(lhs, rhs, subs=None, ref=None):
    """
    Renders a LaTeX equation with an optional substitution step.
    Uses \\times for multiplication.
    """
    if ref:
        st.markdown(f"**Reference:** {ref}")

    st.latex(f"{lhs} = {rhs}")
    
    if subs:
        sub_rhs = rhs
        for key, value in subs.items():
            sub_rhs = sub_rhs.replace(key, f"{value}")
            
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
# 4. STREAMLIT APP LAYOUT
# ==========================================
st.set_page_config(page_title="STAAD Design Calculation", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #ffffff; color: #333; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stApp { background-color: #f0f2f6; }
    h1, h2, h3 { color: #2c3e50; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Input ---
st.sidebar.title("Input")
st.sidebar.markdown("Paste your STAAD report text below:")
raw_input = st.sidebar.text_area("STAAD Output", height=300)

if raw_input:
    try:
        member_data = parse_staad_report(raw_input)
        st.sidebar.success("Parsed successfully!")
    except Exception as e:
        st.sidebar.error(f"Error parsing input: {e}")
        member_data = default_member_data
else:
    st.sidebar.info("Using default example data.")
    member_data = default_member_data

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
# Ensure we have data before iterating
if loads:
    for key, data in loads.items():
        load_table_data.append({
            "Load": key,
            "Value": data.get("value", 0),
            "Unit": data.get("unit", ""),
            "Definition": data.get("desc", "")
        })
    df_loads = pd.DataFrame(load_table_data)
    st.table(df_loads)
else:
    st.write("No load data found.")

# 1.2 Section Properties & Material
c1, c2 = st.columns(2)

with c1:
    st.subheader("1.2 Section Properties")
    props = member_data["properties"]
    if props:
        prop_table_data = [{"Property": k, "Value": v.get("value", 0), "Unit": v.get("unit", "")} for k, v in props.items()]
        st.table(pd.DataFrame(prop_table_data))
    else:
        st.write("No property data found.")

with c2:
    st.subheader("1.3 Material & Parameters")
    mat = member_data["material"]
    par = member_data["params"]
    
    st.markdown("**Material Properties**")
    st.write(f"- Yield Strength ($F_y$): {mat.get('Fyld', 0)} ksi")
    st.write(f"- Ultimate Strength ($F_u$): {mat.get('Fu', 0)} ksi")
    
    st.markdown("**Design Parameters**")
    st.write(f"- Length: {par.get('Length', 0)} in")
    st.write(f"- Effective Length Factors: $K_x={par.get('Kx', 0)}, K_y={par.get('Ky', 0)}$")
    st.write(f"- LTB Modification Factor ($C_b$): {par.get('Cb', 1.0)}")

# --- 1.4 Classification ---
st.header("1.4 Slenderness Classification")
cls = member_data.get("classification", default_member_data["classification"])

c_cls1, c_cls2 = st.columns(2)

with c_cls1:
    st.subheader("Compression (Table B4.1a)")
    comp_cls = cls["compression"]
    
    # Flange
    f_c = comp_cls["flange"]
    st.markdown(f"**Flange**: {f_c['status']}")
    st.write(f"Case: {f_c['case']}")
    st.latex(f"\lambda = {f_c['lambda']}")
    st.latex(f"\lambda_r = {f_c['lambda_r']}")
    if f_c['lambda_r'] != "N/A" and f_c['lambda'] < float(f_c['lambda_r']):
        st.success(f"$\lambda < \lambda_r$ \u2192 Non-Slender")
    else:
        st.warning(f"Check Slenderness")

    st.markdown("---")
    
    # Web
    w_c = comp_cls["web"]
    st.markdown(f"**Web**: {w_c['status']}")
    st.write(f"Case: {w_c['case']}")
    st.latex(f"\lambda = {w_c['lambda']}")
    st.latex(f"\lambda_r = {w_c['lambda_r']}")
    if w_c['lambda_r'] != "N/A" and w_c['lambda'] < float(w_c['lambda_r']):
        st.success(f"$\lambda < \lambda_r$ \u2192 Non-Slender")
    else:
        st.warning(f"Check Slenderness")

with c_cls2:
    st.subheader("Flexure (Table B4.1b)")
    flex_cls = cls["flexure"]
    
    # Flange
    f_f = flex_cls["flange"]
    st.markdown(f"**Flange**: {f_f['status']}")
    st.write(f"Case: {f_f['case']}")
    st.latex(f"\lambda = {f_f['lambda']}")
    st.latex(f"\lambda_p = {f_f['lambda_p']}, \lambda_r = {f_f['lambda_r']}")
    
    if f_f['lambda_p'] != "N/A" and f_f['lambda_r'] != "N/A":
        lp = float(f_f['lambda_p'])
        lr = float(f_f['lambda_r'])
        lam = f_f['lambda']
        if lam <= lp:
            st.success(f"$\lambda \le \lambda_p$ \u2192 Compact")
        elif lam <= lr:
            st.warning(f"$\lambda_p < \lambda \le \lambda_r$ \u2192 Non-Compact")
        else:
            st.error(f"$\lambda > \lambda_r$ \u2192 Slender")

    st.markdown("---")

    # Web
    w_f = flex_cls["web"]
    st.markdown(f"**Web**: {w_f['status']}")
    st.write(f"Case: {w_f['case']}")
    st.latex(f"\lambda = {w_f['lambda']}")
    st.latex(f"\lambda_p = {w_f['lambda_p']}, \lambda_r = {w_f['lambda_r']}")
    
    if w_f['lambda_p'] != "N/A" and w_f['lambda_r'] != "N/A":
        lp = float(w_f['lambda_p'])
        lr = float(w_f['lambda_r'])
        lam = w_f['lambda']
        if lam <= lp:
            st.success(f"$\lambda \le \lambda_p$ \u2192 Compact")
        elif lam <= lr:
            st.warning(f"$\lambda_p < \lambda \le \lambda_r$ \u2192 Non-Compact")
        else:
            st.error(f"$\lambda > \lambda_r$ \u2192 Slender")


# --- 2. Detailed Calculations ---
st.header("2. Detailed Calculations")

checks = member_data["checks"]

# 2.1 Tension
section_header("2.1 Tension Checks")
t_yield = checks.get("tension_yielding", {})
t_rupture = checks.get("tension_rupture", {})

st.markdown("#### Tensile Yielding")
Fy = mat.get("Fyld", 0)
Ag = props.get("Ag", {}).get("value", 0)
Pn_val = t_yield.get('Pn', 0)
if Pn_val == 0: Pn_val = Fy * Ag

render_latex(
    lhs="P_n", 
    rhs="F_y \\times A_g", 
    subs={"F_y": Fy, "A_g": Ag},
    ref=f"{t_yield.get('ref', '')} ({t_yield.get('eqn', '')})"
)
st.latex(f"P_n = {Pn_val} \\text{{ kips}}")

phi = 0.9
phi_pn = phi * Pn_val
render_latex(
    lhs="\phi P_n", 
    rhs=f"{phi} \\times P_n",
    subs={"P_n": Pn_val}
)
st.latex(f"\phi P_n = {phi_pn:.2f} \\text{{ kips}}")
st.latex(f"P_u = {t_yield.get('demand', 0)} \\text{{ kips}}")
result_card("Ratio", t_yield.get("ratio", 0), "", "PASS" if t_yield.get("ratio", 0) < 1.0 else "FAIL")

st.markdown("#### Tensile Rupture")
Fu = mat.get("Fu", 0)
Ae = t_rupture.get("Ae", 0)
Pn_rupture = t_rupture.get('Pn', 0)
if Pn_rupture == 0: Pn_rupture = Fu * Ae

render_latex(
    lhs="P_n", 
    rhs="F_u \\times A_e", 
    subs={"F_u": Fu, "A_e": Ae},
    ref=f"{t_rupture.get('ref', '')} ({t_rupture.get('eqn', '')})"
)
st.latex(f"P_n = {Pn_rupture} \\text{{ kips}}")

phi_rupture = 0.75
phi_pn_rupture = phi_rupture * Pn_rupture
render_latex(
    lhs="\phi P_n", 
    rhs=f"{phi_rupture} \\times P_n",
    subs={"P_n": Pn_rupture}
)
st.latex(f"\phi P_n = {phi_pn_rupture:.2f} \\text{{ kips}}")
st.latex(f"P_u = {t_rupture.get('demand', 0)} \\text{{ kips}}")
result_card("Ratio", t_rupture.get("ratio", 0), "", "PASS" if t_rupture.get("ratio", 0) < 1.0 else "FAIL")


# 2.2 Compression
section_header("2.2 Compression Checks")
comp_x = checks.get("compression_x", {})
comp_y = checks.get("compression_y", {})
phi_comp = 0.9

# X-Axis
st.markdown("#### Flexural Buckling (X-Axis)")
st.write(f"Effective Slenderness ($L_{{cx}}/r_x$): {comp_x.get('Lcx_rx', 0)}")

# FeX
render_latex(
    lhs="F_{ex}",
    rhs="\\frac{\pi^2 \\times E}{(L_{cx}/r_x)^2}",
    subs={"E": "29000", "L_{cx}/r_x": comp_x.get('Lcx_rx', 0)},
    ref="Eq.E3-4"
)
st.latex(f"F_{{ex}} = {comp_x.get('Fex', 0)} \\text{{ ksi}}")

# FcrX
render_latex(
    lhs="F_{crx}",
    rhs="0.658^{F_y/F_{ex}} \\times F_y",
    subs={"F_y": mat.get("Fyld", 0), "F_{ex}": comp_x.get("Fex", 0)},
    ref=f"{comp_x.get('ref', '')} (Eq.E3-2)"
)
st.latex(f"F_{{crx}} = {comp_x.get('Fcrx', 0)} \\text{{ ksi}}")

# PnX
render_latex(
    lhs="P_{nx}",
    rhs="F_{crx} \\times A_g",
    subs={"F_{crx}": comp_x.get("Fcrx", 0), "A_g": props.get("Ag", {}).get("value", 0)},
    ref="Eq.E3-1"
)
st.latex(f"P_{{nx}} = {comp_x.get('Pnx', 0)} \\text{{ kips}}")

# Phi PnX
phi_pnx = phi_comp * comp_x.get('Pnx', 0)
render_latex(
    lhs="\phi P_{nx}",
    rhs=f"{phi_comp} \\times P_{{nx}}",
    subs={"P_{nx}": comp_x.get('Pnx', 0)}
)
st.latex(f"\phi P_{{nx}} = {phi_pnx:.2f} \\text{{ kips}}")
st.latex(f"P_u = {comp_x.get('demand', 0)} \\text{{ kips}}")
result_card("Ratio", comp_x.get("ratio", 0), "", "PASS" if comp_x.get("ratio", 0) < 1.0 else "FAIL")


# Y-Axis
st.markdown("#### Flexural Buckling (Y-Axis)")
st.write(f"Effective Slenderness ($L_{{cy}}/r_y$): {comp_y.get('Lcy_ry', 0)}")

# FeY
render_latex(
    lhs="F_{ey}",
    rhs="\\frac{\pi^2 \\times E}{(L_{cy}/r_y)^2}",
    subs={"E": "29000", "L_{cy}/r_y": comp_y.get('Lcy_ry', 0)},
    ref="Eq.E3-4"
)
st.latex(f"F_{{ey}} = {comp_y.get('Fey', 0)} \\text{{ ksi}}")

# FcrY
render_latex(
    lhs="F_{cry}",
    rhs="0.658^{F_y/F_{ey}} \\times F_y",
    subs={"F_y": mat.get("Fyld", 0), "F_{ey}": comp_y.get("Fey", 0)},
    ref=f"{comp_y.get('ref', '')} (Eq.E3-2)"
)
st.latex(f"F_{{cry}} = {comp_y.get('Fcry', 0)} \\text{{ ksi}}")

# PnY
render_latex(
    lhs="P_{ny}",
    rhs="F_{cry} \\times A_g",
    subs={"F_{cry}": comp_y.get("Fcry", 0), "A_g": props.get("Ag", {}).get("value", 0)},
    ref="Eq.E3-1"
)
st.latex(f"P_{{ny}} = {comp_y.get('Pny', 0)} \\text{{ kips}}")

# Phi PnY
phi_pny = phi_comp * comp_y.get('Pny', 0)
render_latex(
    lhs="\phi P_{ny}",
    rhs=f"{phi_comp} \\times P_{{ny}}",
    subs={"P_{ny}": comp_y.get('Pny', 0)}
)
st.latex(f"\phi P_{{ny}} = {phi_pny:.2f} \\text{{ kips}}")
st.latex(f"P_u = {comp_y.get('demand', 0)} \\text{{ kips}}")
result_card("Ratio", comp_y.get("ratio", 0), "", "PASS" if comp_y.get("ratio", 0) < 1.0 else "FAIL")


# Flexural-Torsional Buckling
ftb = checks.get("ftb", {})
st.markdown("#### Flexural-Torsional Buckling")

# Fe
# Calculate inputs for Fe (Fez and H) as they are not in report
E_val = 29000
G_val = 11200
Cw_val = props.get("Cw", {}).get("value", 0)
J_val = props.get("J", {}).get("value", 0)
Ix_val = props.get("Ixx", {}).get("value", 0)
Iy_val = props.get("Iyy", {}).get("value", 0)
Ag_val = props.get("Ag", {}).get("value", 0)
L_val = par.get("Length", 0)

# Calculate ro2
ro2 = 0
if Ag_val > 0:
    rx2 = Ix_val / Ag_val
    ry2 = Iy_val / Ag_val
    ro2 = rx2 + ry2 # Assuming xo = yo = 0 for doubly symmetric

# Calculate Fez
Fez = 0
if ro2 > 0 and Ag_val > 0 and L_val > 0:
    term1 = (3.14159**2 * E_val * Cw_val) / (L_val**2)
    term2 = G_val * J_val
    Fez = (term1 + term2) * (1 / (Ag_val * ro2))

# Assume H = 1.0 for doubly symmetric
H_val = 1.0

render_latex(
    lhs="F_e",
    rhs="\\left( \\frac{F_{ey} + F_{ez}}{2H} \\right) \\left[ 1 - \\sqrt{1 - \\frac{4 F_{ey} F_{ez} H}{(F_{ey} + F_{ez})^2}} \\right]",
    subs={
        "F_{ey}": comp_y.get("Fey", 0),
        "F_{ez}": f"{Fez:.3f}",
        "H": H_val
    },
    ref=f"{ftb.get('ref', '')} (Eq.E4-2)"
)
st.latex(f"F_e = {ftb.get('Fe', 0)} \\text{{ ksi}}")

# Fcr
render_latex(
    lhs="F_{cr}",
    rhs="0.658^{F_y/F_e} \\times F_y",
    subs={"F_y": mat.get("Fyld", 0), "F_e": ftb.get("Fe", 0)},
    ref="Eq.E3-2"
)
st.latex(f"F_{{cr}} = {ftb.get('Fcr', 0)} \\text{{ ksi}}")

# Pn
render_latex(
    lhs="P_n",
    rhs="F_{cr} \\times A_g",
    subs={"F_{cr}": ftb.get("Fcr", 0), "A_g": props.get("Ag", {}).get("value", 0)},
    ref="Eq.E4-1"
)
st.latex(f"P_n = {ftb.get('Pn', 0)} \\text{{ kips}}")

# Phi Pn
phi_ftb = 0.9
phi_pn_ftb = phi_ftb * ftb.get('Pn', 0)
render_latex(
    lhs="\phi P_n",
    rhs=f"{phi_ftb} \\times P_n",
    subs={"P_n": ftb.get('Pn', 0)}
)
st.latex(f"\phi P_n = {phi_pn_ftb:.2f} \\text{{ kips}}")
st.latex(f"P_u = {ftb.get('demand', 0)} \\text{{ kips}}")
result_card("Ratio", ftb.get("ratio", 0), "", "PASS" if ftb.get("ratio", 0) < 1.0 else "FAIL")


# 2.3 Shear
section_header("2.3 Shear Checks")
shear_x = checks.get("shear_x", {})
shear_y = checks.get("shear_y", {})

c_s1, c_s2 = st.columns(2)
with c_s1:
    st.markdown("#### Shear Along X")
    render_latex(
        lhs="V_{nx}",
        rhs="0.6 \\times F_y \\times A_w \\times C_v",
        subs={"F_y": mat.get("Fyld", 0), "A_w": "Aw", "C_v": shear_x.get("Cv", 0)},
        ref=f"{shear_x.get('ref', '')} (Eq.G2-1)"
    )
    st.latex(f"V_{{nx}} = {shear_x.get('Vnx', 0)} \\text{{ kips}}")
    st.latex(f"V_{{ux}} = {shear_x.get('demand', 0)} \\text{{ kips}}")
    result_card("Ratio", shear_x.get("ratio", 0), "", "PASS" if shear_x.get("ratio", 0) < 1.0 else "FAIL")

with c_s2:
    st.markdown("#### Shear Along Y")
    render_latex(
        lhs="V_{ny}",
        rhs="0.6 \\times F_y \\times A_w \\times C_v",
        subs={"F_y": mat.get("Fyld", 0), "A_w": "Aw", "C_v": shear_y.get("Cv", 0)},
        ref=f"{shear_y.get('ref', '')} (Eq.G2-1)"
    )
    st.latex(f"V_{{ny}} = {shear_y.get('Vny', 0)} \\text{{ kips}}")
    st.latex(f"V_{{uy}} = {shear_y.get('demand', 0)} \\text{{ kips}}")
    result_card("Ratio", shear_y.get("ratio", 0), "", "PASS" if shear_y.get("ratio", 0) < 1.0 else "FAIL")


# 2.4 Bending
section_header("2.4 Bending Checks")
ltb_x = checks.get("ltb_x", {})
flex_y = checks.get("flexure_y", {})
phi_bend = 0.9

# Y-Axis: Flexural Yielding (First as requested)
st.markdown("#### Flexural Yielding (Y-Axis)")
render_latex(
    lhs="M_{ny}",
    rhs="M_p = F_y \\times Z_y",
    subs={"F_y": mat.get("Fyld", 0), "Z_y": props.get("Zyy", {}).get("value", 0)},
    ref=f"{flex_y.get('ref', '')} (Eq.F6-1)"
)
st.latex(f"M_{{ny}} = {flex_y.get('Mny', 0)} \\text{{ kip-in}}")

phi_mny = phi_bend * flex_y.get('Mny', 0)
render_latex(
    lhs="\phi M_{ny}",
    rhs=f"{phi_bend} \\times M_{{ny}}",
    subs={"M_{ny}": flex_y.get('Mny', 0)}
)
st.latex(f"\phi M_{{ny}} = {phi_mny:.2f} \\text{{ kip-in}}")
st.latex(f"M_{{uy}} = {flex_y.get('demand', 0)} \\text{{ kip-in}}")
result_card("Ratio", flex_y.get("ratio", 0), "", "PASS" if flex_y.get("ratio", 0) < 1.0 else "FAIL")


# X-Axis: Lateral Torsional Buckling
st.markdown("#### Lateral Torsional Buckling (X-Axis)")
st.write(f"Unbraced Length ($L_b$): {par.get('Length', 0)} in")

# Lp
render_latex(
    lhs="L_p",
    rhs="1.76 r_y \\sqrt{\\frac{E}{F_y}}",
    subs={"r_y": "ry", "E": "29000", "F_y": mat.get("Fyld", 0)}, # ry not explicitly parsed, simplifying
    ref="Eq.F2-5"
)
st.write(f"**Limiting Length ($L_p$):** {ltb_x.get('Lp', 0)} in")

# Rts
render_latex(
    lhs="R_{ts}",
    rhs="\\sqrt{\\frac{\\sqrt{I_y C_w}}{S_x}}",
    subs={"I_y": props.get("Iyy", {}).get("value", 0), "C_w": props.get("Cw", {}).get("value", 0), "S_x": props.get("Sxx", {}).get("value", 0)},
    ref="Eq.F2-7"
)
st.write(f"**Effective Radius of Gyration ($R_{{ts}}$):** {ltb_x.get('Rts', 0)} in")

# Lr
render_latex(
    lhs="L_r",
    rhs="1.95 R_{ts} \\frac{E}{0.7 F_y} \\sqrt{\\frac{J c}{S_x h_0} + \\sqrt{(\\frac{J c}{S_x h_0})^2 + 6.76 (\\frac{0.7 F_y}{E})^2}}",
    subs={"R_{ts}": ltb_x.get("Rts", 0), "E": "29000", "F_y": mat.get("Fyld", 0)},
    ref="Eq.F2-6"
)
st.write(f"**Limiting Length ($L_r$):** {ltb_x.get('Lr', 0)} in")

# Cb
st.write(f"**Moment Gradient Factor ($C_b$):** {ltb_x.get('Cb', 1.0)}")

# Mnx
render_latex(
    lhs="M_{nx}",
    rhs="C_b \\times [M_p - (M_p - 0.7 \\times F_y \\times S_x) \\times \\frac{L_b - L_p}{L_r - L_p}]",
    subs={
        "C_b": ltb_x.get("Cb", 1.0), 
        "M_p": "Mp", 
        "F_y": mat.get("Fyld", 0),
        "L_b": par.get('Length', 0),
        "L_p": ltb_x.get('Lp', 0),
        "L_r": ltb_x.get('Lr', 0)
    },
    ref=f"{ltb_x.get('ref', '')} (Eq.F2-2)"
)
st.latex(f"M_{{nx}} = {ltb_x.get('Mnx', 0)} \\text{{ kip-in}}")

phi_mnx = phi_bend * ltb_x.get('Mnx', 0)
render_latex(
    lhs="\phi M_{nx}",
    rhs=f"{phi_bend} \\times M_{{nx}}",
    subs={"M_{nx}": ltb_x.get('Mnx', 0)}
)
st.latex(f"\phi M_{{nx}} = {phi_mnx:.2f} \\text{{ kip-in}}")
st.latex(f"M_{{ux}} = {ltb_x.get('demand', 0)} \\text{{ kip-in}}")
result_card("Ratio", ltb_x.get("ratio", 0), "", "PASS" if ltb_x.get("ratio", 0) < 1.0 else "FAIL")


# Flange Local Buckling (X)
flb_x = checks.get("flb_x", {})
st.markdown("#### Flange Local Buckling (X-Axis)")
render_latex(
    lhs="M_{nx}",
    rhs="M_p - (M_p - 0.7 F_y S_x) \\frac{\lambda - \lambda_{pf}}{\lambda_{rf} - \lambda_{pf}}",
    subs={}, 
    ref=f"{flb_x.get('ref', '')} (Eq.F3-1)"
)
st.latex(f"M_{{nx}} = {flb_x.get('Mnx', 0)} \\text{{ kip-in}}")

phi_mnx_flb = phi_bend * flb_x.get('Mnx', 0)
render_latex(
    lhs="\phi M_{nx}",
    rhs=f"{phi_bend} \\times M_{{nx}}",
    subs={"M_{nx}": flb_x.get('Mnx', 0)}
)
st.latex(f"\phi M_{{nx}} = {phi_mnx_flb:.2f} \\text{{ kip-in}}")
st.latex(f"M_{{ux}} = {flb_x.get('demand', 0)} \\text{{ kip-in}}")
result_card("Ratio", flb_x.get("ratio", 0), "", "PASS" if flb_x.get("ratio", 0) < 1.0 else "FAIL")


# Flange Local Buckling (Y)
flb_y = checks.get("flb_y", {})
st.markdown("#### Flange Local Buckling (Y-Axis)")
render_latex(
    lhs="M_{ny}",
    rhs="M_p - (M_p - 0.7 F_y S_y) \\frac{\lambda - \lambda_{pf}}{\lambda_{rf} - \lambda_{pf}}",
    subs={},
    ref=f"{flb_y.get('ref', '')} (Eq.F6-2)"
)
st.latex(f"M_{{ny}} = {flb_y.get('Mny', 0)} \\text{{ kip-in}}")

phi_mny_flb = phi_bend * flb_y.get('Mny', 0)
render_latex(
    lhs="\phi M_{ny}",
    rhs=f"{phi_bend} \\times M_{{ny}}",
    subs={"M_{ny}": flb_y.get('Mny', 0)}
)
st.latex(f"\phi M_{{ny}} = {phi_mny_flb:.2f} \\text{{ kip-in}}")
st.latex(f"M_{{uy}} = {flb_y.get('demand', 0)} \\text{{ kip-in}}")
result_card("Ratio", flb_y.get("ratio", 0), "", "PASS" if flb_y.get("ratio", 0) < 1.0 else "FAIL")


# 2.5 Interaction
section_header("2.5 Interaction Checks")
inter = checks.get("interaction", {})

st.markdown("#### Combined Axial and Flexure")

# Extract values
Pr = loads.get("Pz", {}).get("value", 0)
Pc = inter.get("Pc", 0)
Mrx = abs(loads.get("Mx", {}).get("value", 0))
Mcx = inter.get("Mcx", 0)
Mry = loads.get("My", {}).get("value", 0)
Mcy = inter.get("Mcy", 0)

# Check Pr/Pc ratio
pr_pc_ratio = 0
if Pc != 0:
    pr_pc_ratio = Pr / Pc

st.latex(f"P_r / P_c = {Pr} / {Pc} = {pr_pc_ratio:.3f}")

if pr_pc_ratio < 0.2:
    st.success("Since $P_r / P_c < 0.2$, Equation H1-1b applies.")
    eqn_lhs = "\\frac{P_r}{2P_c} + \\left( \\frac{M_{rx}}{M_{cx}} + \\frac{M_{ry}}{M_{cy}} \\right)"
    ref_eqn = "Eq.H1-1b"
else:
    st.warning("Since $P_r / P_c \ge 0.2$, Equation H1-1a applies.")
    eqn_lhs = "\\frac{P_r}{P_c} + \\frac{8}{9} \\left( \\frac{M_{rx}}{M_{cx}} + \\frac{M_{ry}}{M_{cy}} \\right)"
    ref_eqn = "Eq.H1-1a"

render_latex(
    lhs="Ratio",
    rhs=eqn_lhs,
    subs={
        "P_r": Pr, "P_c": Pc,
        "M_{rx}": Mrx, "M_{cx}": Mcx,
        "M_{ry}": Mry, "M_{cy}": Mcy
    },
    ref=f"{inter.get('criteria', ref_eqn)}"
)

st.metric("Final Interaction Ratio", inter.get("ratio", 0))
if inter.get("ratio", 0) <= 1.0:
    st.success(f"Member PASSES with Ratio {inter.get('ratio', 0)}")
else:
    st.error(f"Member FAILS with Ratio {inter.get('ratio', 0)}")
