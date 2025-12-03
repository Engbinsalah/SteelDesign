 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/app.py b/app.py
new file mode 100644
index 0000000000000000000000000000000000000000..b9de5051d3dfcaa11fc9c893287a6f3d2fd37393
--- /dev/null
+++ b/app.py
@@ -0,0 +1,514 @@
+import math
+import re
+from dataclasses import dataclass
+from typing import Dict, Optional
+
+import pandas as pd
+import streamlit as st
+
+
+DEFAULT_REPORT = """Member :     1
+|-----------------------------------------------------------------------------|
+|  Member No:        1       Profile:  ST  W8X31              (AISC SECTIONS)|
+|  Status:        PASS       Ratio:         0.218       Loadcase:     1006    |
+|  Location:      0.00       Ref:      Eq.H1-1b                              |
+|  Pz:       6.830     C     Vy:       -1.970           Vx:     -.2474       |
+|  Tz:      -2.469           My:        9.130           Mx:     -243.2       |
+|-----------------------------------------------------------------------------|
+| COMPRESSION SLENDERNESS                                                      |
+| Actual Slenderness Ratio    :     87.309                                    |
+| Allowable Slenderness Ratio :    200.000            LOC :     0.00          |
+|-----------------------------------------------------------------------------|
+| STRENGTH CHECKS                                                              |
+| Critical L/C  :   1006             Ratio     :        0.218(PASS)           |
+|          Loc  :    0.00            Condition :    Eq.H1-1b                  |
+|-----------------------------------------------------------------------------|
+| SECTION PROPERTIES  (LOC:     0.00, PROPERTIES UNIT: IN  )                  |
+| Ag  :   9.130E+00     Axx :   6.960E+00     Ayy :   2.280E+00               |
+| Ixx :   1.100E+02     Iyy :   3.710E+01     J   :   5.360E-01               |
+| Sxx+:   2.750E+01     Sxx-:   2.750E+01     Zxx :   3.040E+01               |
+| Syy+:   9.275E+00     Syy-:   9.275E+00     Zyy :   1.410E+01               |
+| Cw  :   5.311E+02     x0  :   0.000E+00     y0  :   0.000E+00               |
+|-----------------------------------------------------------------------------|
+| MATERIAL PROPERTIES                                                         |
+| Fyld:          50.000             Fu:          62.000                       |
+|-----------------------------------------------------------------------------|
+| Actual Member Length:       121.000                                         |
+| Design Parameters                                  (Rolled)                 |
+| Kx:    2.00  Ky:    2.00  NSF:    1.00  SLF:    1.00  CSP:   12.00          |
+|-----------------------------------------------------------------------------|
+| COMPRESSION CLASSIFICATION (L/C:   1030 LOC:     0.00)                      |
+|                          λ         λp        λr       CASE                  |
+| Flange: NonSlender       9.20       N/A      13.49     Table.4.1a.Case1     |
+| Web   : NonSlender      22.25       N/A      35.88     Table.4.1a.Case5     |
+|                                                                             |
+| FLEXURE CLASSIFICATION     (L/C:     43 LOC:     0.00)                      |
+|                          λ         λp        λr       CASE                  |
+| Flange: NonCompact       9.20       9.15     24.08     Table.4.1b.Case10    |
+| Web   : Compact         22.25      90.55    137.27     Table.4.1b.Case15    |
+|-----------------------------------------------------------------------------|
+| CHECKS FOR AXIAL TENSION                                                    |
+|-----------------------------------------------------------------------------|
+| TENSILE YIELDING                                                           |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|              0.000       410.9       0.000     Cl.D2      1000      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Nom. Ten. Yld Cap        : Pn     =  456.50     kip        Eq.D2-1         |
+|-----------------------------------------------------------------------------|
+| TENSILE RUPTURE                                                           |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|              0.000       424.5       0.000     Cl.D2      1000      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Effective area           : Ae     =  9.1300     in2        Eq.D3-1         |
+|  Nom. Ten. Rpt Cap        : Pn     =  566.06     kip        Eq.D2-2         |
+|-----------------------------------------------------------------------------|
+| CHECKS FOR AXIAL COMPRESSION                                               |
+| FLEXURAL BUCKLING X                                                        |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|              8.409       319.2       0.026     Cl.E3      1030      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Effective Slenderness     : Lcx/rx =  58.772                Cl.E2          |
+|  Elastic Buckling Stress   : Fex    =  82.863     ksi        Eq.E3-4        |
+|  Crit. Buckling Stress     : Fcrx   =  38.841     ksi        Eq.E3-2        |
+|  Nom. Flexural Buckling    : Pnx    =  354.61     kip        Eq.E3-1        |
+|-----------------------------------------------------------------------------|
+| FLEXURAL BUCKLING Y                                                        |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|              8.409       235.3       0.036     Cl.E3      1030      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Effective Slenderness     : Lcy/ry =  87.309                Cl.E2          |
+|  Elastic Buckling Stress   : Fey    =  37.547     ksi        Eq.E3-4        |
+|  Crit. Buckling Stress     : Fcry   =  28.636     ksi        Eq.E3-2        |
+|  Nom. Flexural Buckling    : Pny    =  261.44     kip        Eq.E3-1        |
+|-----------------------------------------------------------------------------|
+| FLEXURAL-TORSIONAL-BUCKLING                                                |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|              8.409       340.4       0.025     Cl.E4      1030      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Elastic F-T-B Stress      : Fe     =  111.22     ksi        Eq.E4-2        |
+|  Crit. F-T-B Stress        : Fcr    =  41.424     ksi        Eq.E3-2        |
+|  Nom. Flex-tor Buckling    : Pn     =  378.20     kip        Eq.E4-1        |
+|-----------------------------------------------------------------------------|
+| CHECKS FOR SHEAR                                                            |
+|-----------------------------------------------------------------------------|
+| SHEAR ALONG X                                                               |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|              1.360       187.9       0.007     Cl.G1      1032      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Coefficient Cv Along X    : Cv     =  1.0000                Eq.G2-9        |
+|  Coefficient Kv Along X    : Kv     =  1.2000                Cl.G6          |
+|  Nom. Shear Along X        : Vnx    =  208.80     kip        Eq.G6-1        |
+|-----------------------------------------------------------------------------|
+| SHEAR ALONG Y                                                               |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|              1.970       68.40       0.029     Cl.G1      1005      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Coefficient Cv Along Y    : Cv     =  1.0000                -              |
+|  Coefficient Kv Along Y    : Kv     =  5.3400                Eq.G2-5        |
+|  Nom. Shear Along Y        : Vny    =  68.400     kip        Eq.G2-1        |
+|-----------------------------------------------------------------------------|
+| CHECKS FOR BENDING                                                          |
+|-----------------------------------------------------------------------------|
+| FLEXURAL YIELDING (Y)                                                       |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|            -83.49       634.5       0.132     Cl.F6.1     1032      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Nom Flex Yielding Along Y : Mny    =  705.00     kip-in     Eq.F6-1        |
+|-----------------------------------------------------------------------------|
+| LAT TOR BUCK ABOUT X                                                        |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|            -243.2       1284.       0.189     Cl.F2.2     1004      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Nom L-T-B Cap             : Mnx    =  1426.5     kip-in     Eq.F2-2        |
+|  Mom. Distr. factor        : CbX    =  1.0000                Custom         |
+|  Limiting Unbraced Length  : LpX    =  85.443     in         Eq.F2-5        |
+|  coefficient C             : Cx     =  1.0000                Eq.F2-8a       |
+|  Effective Rad. of Gyr.    : Rts    =  2.2593     in         Eq.F2-7        |
+|  Limiting Unbraced Length  : LrX    =  297.38     in         Eq.F2-6        |
+|-----------------------------------------------------------------------------|
+| FLANGE LOCAL BUCK(X)                                                        |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|            -243.2       1367.       0.178     Cl.F3.1     1004      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Nom F-L-B Cap             : Mnx    =  1518.4     kip-in     Eq.F3-1        |
+|-----------------------------------------------------------------------------|
+| FLANGE LOCAL BUCK(Y)                                                        |
+|              DEMAND      CAPACITY    RATIO     REFERENCE    L/C    LOC      |
+|            -83.49       633.5       0.132     Cl.F6.2     1032      0.00    |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Nom F-L-B Cap             : Mny    =  703.88     kip-in     Eq.F6-2        |
+|-----------------------------------------------------------------------------|
+| CHECKS FOR AXIAL BEND INTERACTION                                           |
+|-----------------------------------------------------------------------------|
+| COMBINED FORCES CLAUSE H1                                                   |
+|                            RATIO      CRITERIA           L/C      LOC       |
+|                            0.218      Eq.H1-1b         1006       0.00      |
+|                                                                             |
+| Intermediate Results :                                                     |
+|  Axial Capacity            : Pc     =  235.30     kip        Cl.H1.1        |
+|  Moment Capacity           : Mcx    =  1283.8     kip-in     Cl.H1.1        |
+|  Moment Capacity           : Mcy    =  633.50     kip-in     Cl.H1.1        |
+|-----------------------------------------------------------------------------|"""
+
+
+@dataclass
+class SectionProperties:
+    ag: float
+    ixx: float
+    iyy: float
+    zxx: float
+    zyy: float
+    sxx: float
+    syy: float
+
+
+@dataclass
+class MaterialProperties:
+    fy: float
+    fu: float
+
+
+def extract_value(pattern: str, text: str, cast=float) -> Optional[float]:
+    match = re.search(pattern, text, re.MULTILINE)
+    if match:
+        try:
+            return cast(match.group(1).replace(",", ""))
+        except ValueError:
+            return None
+    return None
+
+
+def parse_report(text: str) -> Dict[str, float]:
+    values: Dict[str, float] = {}
+    values["member_no"] = extract_value(r"Member No:\s*(\d+)", text, int)
+    values["profile"] = extract_value(r"Profile:\s*([A-Z0-9 ]+X\d+)", text, str)
+    values["status"] = extract_value(r"Status:\s*([A-Z]+)", text, str)
+    values["ratio"] = extract_value(r"Ratio:\s*([0-9.]+)", text)
+    values["loadcase"] = extract_value(r"Loadcase:\s*(\d+)", text, int)
+    values["location"] = extract_value(r"Location:\s*([-0-9.]+)", text)
+    values["ref"] = extract_value(r"Ref:\s*([A-Za-z0-9.\-]+)", text, str)
+
+    for label in ["Pz", "Vy", "Vx", "Tz", "My", "Mx"]:
+        values[label.lower()] = extract_value(fr"{label}:\s*([-0-9.]+)", text)
+
+    values["actual_slenderness"] = extract_value(r"Actual Slenderness Ratio\s*:\s*([-0-9.]+)", text)
+    values["allowable_slenderness"] = extract_value(r"Allowable Slenderness Ratio\s*:\s*([-0-9.]+)", text)
+
+    # section properties
+    values.update(
+        {
+            "ag": extract_value(r"Ag\s*:\s*([0-9.E+-]+)", text),
+            "ixx": extract_value(r"Ixx\s*:\s*([0-9.E+-]+)", text),
+            "iyy": extract_value(r"Iyy\s*:\s*([0-9.E+-]+)", text),
+            "zxx": extract_value(r"Zxx\s*:\s*([0-9.E+-]+)", text),
+            "zyy": extract_value(r"Zyy\s*:\s*([0-9.E+-]+)", text),
+            "sxx": extract_value(r"Sxx\+?:\s*([0-9.E+-]+)", text),
+            "syy": extract_value(r"Syy\+?:\s*([0-9.E+-]+)", text),
+        }
+    )
+
+    values["fy"] = extract_value(r"Fyld:\s*([0-9.]+)", text)
+    values["fu"] = extract_value(r"Fu:\s*([0-9.]+)", text)
+    values["length"] = extract_value(r"Actual Member Length:\s*([0-9.]+)", text)
+
+    for param in ["Kx", "Ky", "NSF", "SLF", "CSP"]:
+        values[param.lower()] = extract_value(fr"{param}:\s*([0-9.]+)", text)
+
+    values["lcx_over_rx"] = extract_value(r"Lcx/rx\s*=\s*([0-9.]+)", text)
+    values["lcy_over_ry"] = extract_value(r"Lcy/ry\s*=\s*([0-9.]+)", text)
+    values["fex"] = extract_value(r"Fex\s*=\s*([0-9.]+)", text)
+    values["fey"] = extract_value(r"Fey\s*=\s*([0-9.]+)", text)
+    values["fe_ftb"] = extract_value(r"Fe\s*=\s*([0-9.]+)\s*ksi\s*\n\|\s*Crit\. F-T-B Stress\s*:\s*Fcr\s*=", text)
+    values["fcrx"] = extract_value(r"Fcrx\s*=\s*([0-9.]+)", text)
+    values["fcry"] = extract_value(r"Fcry\s*=\s*([0-9.]+)", text)
+    values["fcr_ftb"] = extract_value(r"Crit\. F-T-B Stress\s*:\s*Fcr\s*=\s*([0-9.]+)", text)
+
+    values["cbx"] = extract_value(r"CbX\s*=\s*([0-9.]+)", text)
+    values["lpx"] = extract_value(r"LpX\s*=\s*([0-9.]+)", text)
+    values["lrx"] = extract_value(r"LrX\s*=\s*([0-9.]+)", text)
+    values["rts"] = extract_value(r"Rts\s*=\s*([0-9.]+)", text)
+
+    values["mn_ltb"] = extract_value(r"Nom L-T-B Cap\s*:\s*Mnx\s*=\s*([0-9.]+)", text)
+    values["mn_flb_x"] = extract_value(r"Nom F-L-B Cap\s*:\s*Mnx\s*=\s*([0-9.]+)", text)
+    values["mn_flb_y"] = extract_value(r"Nom F-L-B Cap\s*:\s*Mny\s*=\s*([0-9.]+)", text)
+
+    values["pn_tensile_yield"] = extract_value(r"Nom\. Ten\. Yld Cap\s*:\s*Pn\s*=\s*([0-9.]+)", text)
+    values["pn_tensile_rupture"] = extract_value(r"Nom\. Ten\. Rpt Cap\s*:\s*Pn\s*=\s*([0-9.]+)", text)
+    values["ae"] = extract_value(r"Effective area\s*:\s*Ae\s*=\s*([0-9.]+)", text)
+
+    values["pnx"] = extract_value(r"Nom\. Flexural Buckling\s*:\s*Pnx\s*=\s*([0-9.]+)", text)
+    values["pny"] = extract_value(r"Nom\. Flexural Buckling\s*:\s*Pny\s*=\s*([0-9.]+)", text)
+    values["pn_ftb"] = extract_value(r"Nom\. Flex-tor Buckling\s*:\s*Pn\s*=\s*([0-9.]+)", text)
+
+    values["pc"] = extract_value(r"Axial Capacity\s*:\s*Pc\s*=\s*([0-9.]+)", text)
+    values["mcx"] = extract_value(r"Moment Capacity\s*:\s*Mcx\s*=\s*([0-9.]+)", text)
+    values["mcy"] = extract_value(r"Moment Capacity\s*:\s*Mcy\s*=\s*([0-9.]+)", text)
+
+    return values
+
+
+def tensile_capacity(values: Dict[str, float]) -> Dict[str, float]:
+    ag = values["ag"]
+    fy = values["fy"]
+    fu = values["fu"]
+    ae = values.get("ae", ag)
+    phi_y = 0.9
+    phi_r = 0.75
+
+    pn_y = fy * ag
+    phi_pn_y = phi_y * pn_y
+    pn_r = fu * ae
+    phi_pn_r = phi_r * pn_r
+
+    return {
+        "Pn_yield": pn_y,
+        "phiPn_yield": phi_pn_y,
+        "Pn_rupture": pn_r,
+        "phiPn_rupture": phi_pn_r,
+    }
+
+
+def fcr_from_fe(fe: float, fy: float) -> float:
+    if fe / fy <= 2.25:
+        return 0.658 ** (fe / fy) * fy
+    return 0.877 * fe
+
+
+def compression_capacity(values: Dict[str, float]) -> Dict[str, float]:
+    ag = values["ag"]
+    fy = values["fy"]
+    e = 29000.0
+
+    lcx_rx = values.get("lcx_over_rx")
+    lcy_ry = values.get("lcy_over_ry")
+
+    fe_x = (math.pi**2 * e) / (lcx_rx**2) if lcx_rx else None
+    fe_y = (math.pi**2 * e) / (lcy_ry**2) if lcy_ry else None
+
+    fcr_x = fcr_from_fe(fe_x, fy) if fe_x else None
+    fcr_y = fcr_from_fe(fe_y, fy) if fe_y else None
+
+    pn_x = fcr_x * ag if fcr_x else None
+    pn_y = fcr_y * ag if fcr_y else None
+
+    fe_ftb = values.get("fe_ftb")
+    fcr_ftb = fcr_from_fe(fe_ftb, fy) if fe_ftb else None
+    pn_ftb = fcr_ftb * ag if fcr_ftb else None
+
+    return {
+        "Fe_x": fe_x,
+        "Fcr_x": fcr_x,
+        "Pn_x": pn_x,
+        "Fe_y": fe_y,
+        "Fcr_y": fcr_y,
+        "Pn_y": pn_y,
+        "Fe_ftb": fe_ftb,
+        "Fcr_ftb": fcr_ftb,
+        "Pn_ftb": pn_ftb,
+    }
+
+
+def flexural_capacity(values: Dict[str, float]) -> Dict[str, float]:
+    fy = values["fy"]
+    zxx = values["zxx"]
+    zyy = values["zyy"]
+    sxx = values["sxx"]
+    syy = values["syy"]
+    cb = values.get("cbx", 1.0)
+    lp = values.get("lpx", 0)
+    lr = values.get("lrx", 0)
+    lb = values.get("length", 0)
+
+    mp_x = fy * zxx
+    mr_x = 0.7 * fy * sxx
+    if lr and lp and lr > lp:
+        mn_ltb = cb * (mp_x - (mp_x - mr_x) * (lb - lp) / (lr - lp))
+    else:
+        mn_ltb = mp_x
+
+    lambda_f = extract_value(r"Flange: [A-Za-z]+\s+([0-9.]+)\s+\S+\s+([0-9.]+)\s+([0-9.]+)", values.get("raw_text", ""))
+    # fallback using provided table values
+    lam = values.get("flange_lambda", 9.2) if lambda_f is None else lambda_f
+    lam_p = values.get("flange_lp", 9.15)
+    lam_r = values.get("flange_lr", 24.08)
+
+    mp_y = fy * zyy
+    mr_y = 0.7 * fy * syy
+
+    def non_compact_mn(mp: float, mr: float) -> float:
+        if lam_r and lam_p and lam_r > lam_p:
+            return mp - (mp - mr) * (lam - lam_p) / (lam_r - lam_p)
+        return mp
+
+    mn_flb_x = non_compact_mn(mp_x, mr_x)
+    mn_flb_y = non_compact_mn(mp_y, mr_y)
+
+    mn_yield_y = fy * zyy
+
+    return {
+        "Mp_x": mp_x,
+        "Mr_x": mr_x,
+        "Mn_LTB": mn_ltb,
+        "Mn_FLB_x": mn_flb_x,
+        "Mp_y": mp_y,
+        "Mr_y": mr_y,
+        "Mn_FLB_y": mn_flb_y,
+        "Mn_yield_y": mn_yield_y,
+    }
+
+
+def interaction_ratio(values: Dict[str, float]) -> Optional[float]:
+    pu = abs(values.get("pz", 0.0))
+    pc = values.get("pc")
+    mux = abs(values.get("mx", 0.0))
+    muy = abs(values.get("my", 0.0))
+    mcx = values.get("mcx")
+    mcy = values.get("mcy")
+
+    if None in (pc, mcx, mcy):
+        return None
+
+    term_axial = pu / pc if pc else 0
+    term_moment = mux / mcx + muy / mcy
+    if term_axial <= 0.2:
+        return term_axial / 2 + term_moment
+    return term_axial + (8 / 9) * term_moment
+
+
+def display_table(title: str, data: Dict[str, str]):
+    st.subheader(title)
+    df = pd.DataFrame([data]).T.reset_index()
+    df.columns = ["Parameter", "Value"]
+    st.table(df)
+
+
+def main():
+    st.set_page_config(page_title="STAAD Steel Member Calculation Sheet", layout="wide")
+    st.title("STAAD Steel Member Calculation Sheet")
+    st.caption("Generate a reader-friendly calculation sheet that traces STAAD.Pro CONNECT steel design output to AISC 360-16 equations.")
+
+    with st.expander("Paste STAAD design report excerpt", expanded=True):
+        report_text = st.text_area("STAAD report text", value=DEFAULT_REPORT, height=320)
+
+    values = parse_report(report_text)
+    values["raw_text"] = report_text
+
+    st.markdown("### Input summary")
+    input_data = {
+        "Member": values.get("member_no"),
+        "Profile": values.get("profile"),
+        "Status": values.get("status"),
+        "Critical ratio": values.get("ratio"),
+        "Critical load case": values.get("loadcase"),
+        "Check reference": values.get("ref"),
+        "Location": f"{values.get('location', 0):.2f} in" if values.get("location") is not None else "-",
+    }
+    display_table("General", input_data)
+
+    loads = {
+        "Axial (Pz)": f"{values.get('pz', 0):.3f} kip",
+        "Shear about y (Vy)": f"{values.get('vy', 0):.3f} kip",
+        "Shear about x (Vx)": f"{values.get('vx', 0):.3f} kip",
+        "Torsion (Tz)": f"{values.get('tz', 0):.3f} kip-in",
+        "Moment about y (My)": f"{values.get('my', 0):.3f} kip-in",
+        "Moment about x (Mx)": f"{values.get('mx', 0):.3f} kip-in",
+    }
+    display_table("Factored demand", loads)
+
+    section_props = SectionProperties(
+        ag=values.get("ag", 0),
+        ixx=values.get("ixx", 0),
+        iyy=values.get("iyy", 0),
+        zxx=values.get("zxx", 0),
+        zyy=values.get("zyy", 0),
+        sxx=values.get("sxx", 0),
+        syy=values.get("syy", 0),
+    )
+    section_table = {
+        "Ag": f"{section_props.ag:.3f} in²",
+        "Ixx": f"{section_props.ixx:.2f} in⁴",
+        "Iyy": f"{section_props.iyy:.2f} in⁴",
+        "Zx": f"{section_props.zxx:.2f} in³",
+        "Zy": f"{section_props.zyy:.2f} in³",
+        "Sx": f"{section_props.sxx:.2f} in³",
+        "Sy": f"{section_props.syy:.2f} in³",
+    }
+    display_table("Section properties", section_table)
+
+    material = MaterialProperties(fy=values.get("fy", 0), fu=values.get("fu", 0))
+    display_table("Material", {"Fy": f"{material.fy:.1f} ksi", "Fu": f"{material.fu:.1f} ksi"})
+
+    design_params = {"Kx": values.get("kx"), "Ky": values.get("ky"), "Unbraced length": f"{values.get('length', 0):.1f} in"}
+    display_table("Design parameters", design_params)
+
+    st.markdown("---")
+    st.header("Design checks")
+
+    st.subheader("Axial tension (AISC 360-16 Cl. D2)")
+    tension = tensile_capacity(values)
+    st.latex(r"\phi P_n = 0.9 F_y A_g = 0.9 \times %.2f \times %.3f = %.1f\ \text{kips}" % (material.fy, section_props.ag, tension["phiPn_yield"]))
+    st.write("Report capacity: {:.1f} kips".format(values.get("pn_tensile_yield", 0) * 0.9 if values.get("pn_tensile_yield") else tension["phiPn_yield"]))
+    st.latex(r"\phi P_n = 0.75 F_u A_e = 0.75 \times %.2f \times %.3f = %.1f\ \text{kips}" % (material.fu, values.get("ae", section_props.ag), tension["phiPn_rupture"]))
+
+    st.subheader("Axial compression (AISC 360-16 Cl. E)")
+    comp = compression_capacity(values)
+    if comp["Fe_x"]:
+        st.latex(
+            r"F_{e,x} = \frac{\pi^2 E}{(L_c/r_x)^2} = \frac{\pi^2 \times 29000}{(%.3f)^2} = %.2f\ \text{ksi}" % (values.get("lcx_over_rx"), comp["Fe_x"])
+        )
+        st.latex(r"F_{cr,x} = 0.658^{F_{e,x}/F_y} F_y = 0.658^{%.3f/%.1f} \times %.1f = %.3f\ \text{ksi}" % (comp["Fe_x"], material.fy, material.fy, comp["Fcr_x"]))
+        st.latex(r"\phi P_{n,x} = 0.9 F_{cr,x} A_g = 0.9 \times %.3f \times %.3f = %.2f\ \text{kips}" % (comp["Fcr_x"], section_props.ag, 0.9 * comp["Pn_x"]))
+
+    if comp["Fe_y"]:
+        st.latex(
+            r"F_{e,y} = \frac{\pi^2 E}{(L_c/r_y)^2} = \frac{\pi^2 \times 29000}{(%.3f)^2} = %.2f\ \text{ksi}" % (values.get("lcy_over_ry"), comp["Fe_y"])
+        )
+        st.latex(r"F_{cr,y} = 0.658^{F_{e,y}/F_y} F_y = 0.658^{%.3f/%.1f} \times %.1f = %.3f\ \text{ksi}" % (comp["Fe_y"], material.fy, material.fy, comp["Fcr_y"]))
+        st.latex(r"\phi P_{n,y} = 0.9 F_{cr,y} A_g = 0.9 \times %.3f \times %.3f = %.2f\ \text{kips}" % (comp["Fcr_y"], section_props.ag, 0.9 * comp["Pn_y"]))
+
+    st.subheader("Flexural strength")
+    flex = flexural_capacity(values)
+    st.latex(
+        r"M_{p,x} = F_y Z_x = %.1f \times %.3f = %.1f\ \text{kip-in}" % (material.fy, section_props.zxx, flex["Mp_x"])
+    )
+    st.latex(r"M_{r,x} = 0.7 F_y S_x = 0.7 \times %.1f \times %.3f = %.1f\ \text{kip-in}" % (material.fy, section_props.sxx, flex["Mr_x"]))
+    st.latex(
+        r"M_{n,LTB} = C_b \left[M_p - (M_p - M_r) \frac{L_b - L_p}{L_r - L_p}\right] = %.2f\ \text{kip-in}" % flex["Mn_LTB"]
+    )
+    st.write("Reported LTB capacity: {:.1f} kip-in".format(values.get("mn_ltb", flex["Mn_LTB"])))
+
+    st.latex(
+        r"M_{n,FLB,x} = M_p - (M_p - M_r) \frac{\lambda - \lambda_p}{\lambda_r - \lambda_p} = %.1f\ \text{kip-in}" % flex["Mn_FLB_x"]
+    )
+    st.write("Reported flange local buckling (x) capacity: {:.1f} kip-in".format(values.get("mn_flb_x", flex["Mn_FLB_x"])))
+
+    st.latex(r"M_{p,y} = F_y Z_y = %.1f \times %.3f = %.1f\ \text{kip-in}" % (material.fy, section_props.zyy, flex["Mp_y"]))
+    st.latex(
+        r"M_{n,FLB,y} = M_p - (M_p - 0.7 F_y S_y) \frac{\lambda - \lambda_p}{\lambda_r - \lambda_p} = %.1f\ \text{kip-in}" % flex["Mn_FLB_y"]
+    )
+    st.write("Reported flexural yielding (y) capacity: {:.1f} kip-in".format(values.get("mn_flb_y", flex["Mn_FLB_y"])))
+
+    st.subheader("Interaction (AISC 360-16 Eq. H1-1b)")
+    ratio = interaction_ratio(values)
+    if ratio is not None:
+        st.latex(
+            r"H_1 = \frac{P_u}{P_c} + \frac{8}{9}\left(\frac{M_{ux}}{M_{cx}} + \frac{M_{uy}}{M_{cy}}\right) = %.3f" % ratio
+        )
+        st.write("STAAD reported ratio: {:.3f}".format(values.get("ratio", 0)))
+
+    st.markdown("\n---\nDesigned for traceability: every calculation mirrors the STAAD output order and cites the AISC 360-16 reference used in the report.")
+
+
+if __name__ == "__main__":
+    main()
 
EOF
)
