import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import pydeck as pdk
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Weld Group Analyzer Pro", layout="wide", page_icon="🏗️")

# --- CLASS DEFINITIONS ---
class WeldGroup:
    def __init__(self):
        self.segments = []
        self.properties = {}
        
    def add_segment(self, x1, y1, x2, y2, label=""):
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if length == 0:
            return 
            
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        
        # Moments of inertia of line segment about its own centroid
        ix_o = length * (y2 - y1)**2 / 12
        iy_o = length * (x2 - x1)**2 / 12
        
        self.segments.append({
            'label': label,
            'x1': x1, 'y1': y1,
            'x2': x2, 'y2': y2,
            'L': length,
            'cx': cx, 'cy': cy,
            'ix_o': ix_o, 'iy_o': iy_o
        })

    def calculate_properties(self):
        if not self.segments:
            return False
            
        df = pd.DataFrame(self.segments)
        total_L = df['L'].sum()
        
        # Group Centroid
        cg_x = (df['L'] * df['cx']).sum() / total_L
        cg_y = (df['L'] * df['cy']).sum() / total_L
        
        # Moments of Inertia about Group Centroid (Parallel Axis Theorem)
        I_x = (df['ix_o'] + df['L'] * (df['cy'] - cg_y)**2).sum()
        I_y = (df['iy_o'] + df['L'] * (df['cx'] - cg_x)**2).sum()
        J = I_x + I_y
        
        self.properties = {
            'L_total': total_L,
            'cg_x': cg_x,
            'cg_y': cg_y,
            'I_x': I_x,
            'I_y': I_y,
            'J': J
        }
        return True

    def calculate_stresses(self, loads):
        props = self.properties
        results = []
        max_f = 0
        
        for seg in self.segments:
            for pt_type, x, y in [('Start', seg['x1'], seg['y1']), ('End', seg['x2'], seg['y2'])]:
                rx = x - props['cg_x']
                ry = y - props['cg_y']
                
                # Forces
                fx_total = (loads['Px']/props['L_total']) - (loads['Mz']*ry/props['J'])
                fy_total = (loads['Py']/props['L_total']) + (loads['Mz']*rx/props['J'])
                fz_total = (loads['Pz']/props['L_total']) + (loads['Mx']*ry/props['I_x']) - (loads['My']*rx/props['I_y'])
                
                f_resultant = np.sqrt(fx_total**2 + fy_total**2 + fz_total**2)
                
                if f_resultant > max_f:
                    max_f = f_resultant
                
                results.append({
                    'Segment': seg['label'],
                    'Point': pt_type,
                    'X': x, 'Y': y,
                    'fx': fx_total,
                    'fy': fy_total,
                    'fz': fz_total,
                    'f_res': f_resultant
                })
                
        return pd.DataFrame(results), max_f

# --- UI LAYOUT ---
st.title("🏗️ Weld Group Analyzer Pro")
st.markdown("Calculate capacity, visualize in 3D, and export reports.")

# Create Main Tabs
main_tabs = st.tabs(["1. Calculator & 2D", "2. 3D Visualization", "3. Export Report", "4. Theory"])

# --- SIDEBAR: INPUTS ---
st.sidebar.header("1. Applied Loads")
load_type = st.sidebar.radio("Load Input Method", ["Forces + Coordinates", "Forces + Direct Moments"])

P_x = st.sidebar.number_input("Px (kips) [Shear X]", value=0.0)
P_y = st.sidebar.number_input("Py (kips) [Shear Y]", value=0.0)
P_z = st.sidebar.number_input("Pz (kips) [Axial Z]", value=0.0)

# Initialize variables
M_x_calc, M_y_calc, M_z_calc = 0.0, 0.0, 0.0
load_x, load_y, load_z = 0.0, 0.0, 0.0
add_Mx, add_My, add_Mz = 0.0, 0.0, 0.0

if load_type == "Forces + Coordinates":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Load Application Point:**")
    load_x = st.sidebar.number_input("Load X (in)", value=0.0)
    load_y = st.sidebar.number_input("Load Y (in)", value=0.0)
    load_z = st.sidebar.number_input("Load Z (in)", value=10.0)
    
    st.sidebar.markdown("**Additional Moments:**")
    add_Mx = st.sidebar.number_input("Add'l Mx (k-in)", value=0.0)
    add_My = st.sidebar.number_input("Add'l My (k-in)", value=0.0)
    add_Mz = st.sidebar.number_input("Add'l Mz (k-in)", value=0.0)
else:
    st.sidebar.markdown("---")
    M_x_input = st.sidebar.number_input("Mx (k-in)", value=0.0)
    M_y_input = st.sidebar.number_input("My (k-in)", value=0.0)
    M_z_input = st.sidebar.number_input("Mz (k-in)", value=0.0)

st.sidebar.header("2. Weld Criteria")
F_exx = st.sidebar.selectbox("Electrode Strength", [70, 60, 80, 90, 100], index=0)
phi = st.sidebar.number_input("Phi", value=0.75)
provided_size = st.sidebar.selectbox("Provided Leg Size (in)", 
                                     [0.1875, 0.25, 0.3125, 0.375, 0.5, 0.625, 0.75], 
                                     index=1)

# --- GLOBAL GEOMETRY SETUP ---
# We define geometry first so it's available to all tabs
weld_group = WeldGroup()
shape_type = st.sidebar.selectbox("Geometry Shape", ["Linear", "Rectangle (Box)", "C-Shape", "I/W-Profile", "Custom"])

if shape_type == "Linear":
    l_len = st.sidebar.number_input("Length (in)", value=10.0)
    angle = st.sidebar.number_input("Angle (deg)", value=0.0)
    rad = np.radians(angle)
    weld_group.add_segment(-l_len/2*np.cos(rad), -l_len/2*np.sin(rad), 
                           l_len/2*np.cos(rad), l_len/2*np.sin(rad), "Line")
    
elif shape_type == "Rectangle (Box)":
    w = st.sidebar.number_input("Width (X)", value=10.0)
    h = st.sidebar.number_input("Height (Y)", value=10.0)
    weld_group.add_segment(-w/2, h/2, w/2, h/2, "Top")
    weld_group.add_segment(w/2, h/2, w/2, -h/2, "Right")
    weld_group.add_segment(w/2, -h/2, -w/2, -h/2, "Bottom")
    weld_group.add_segment(-w/2, -h/2, -w/2, h/2, "Left")
    
elif shape_type == "C-Shape":
    w = st.sidebar.number_input("Web Depth (Y)", value=10.0)
    f = st.sidebar.number_input("Flange Width (X)", value=5.0)
    orient = st.sidebar.selectbox("Direction", ["Right", "Left"])
    if orient == "Right":
        weld_group.add_segment(f, w/2, 0, w/2, "Top")
        weld_group.add_segment(0, w/2, 0, -w/2, "Web")
        weld_group.add_segment(0, -w/2, f, -w/2, "Bot")
    else:
        weld_group.add_segment(-f, w/2, 0, w/2, "Top")
        weld_group.add_segment(0, w/2, 0, -w/2, "Web")
        weld_group.add_segment(0, -w/2, -f, -w/2, "Bot")
        
elif shape_type == "I/W-Profile":
    d = st.sidebar.number_input("Depth (d)", value=12.0)
    bf = st.sidebar.number_input("Flange (bf)", value=6.0)
    pat = st.sidebar.radio("Pattern", ["All Around", "I-Shape"])
    if pat == "I-Shape":
        weld_group.add_segment(-bf/2, d/2, bf/2, d/2, "Top Flg")
        weld_group.add_segment(-bf/2, -d/2, bf/2, -d/2, "Bot Flg")
        weld_group.add_segment(0, d/2, 0, -d/2, "Web")
    else:
        weld_group.add_segment(-bf/2, d/2, bf/2, d/2, "Top")
        weld_group.add_segment(bf/2, d/2, bf/2, -d/2, "Right")
        weld_group.add_segment(bf/2, -d/2, -bf/2, -d/2, "Bot")
        weld_group.add_segment(-bf/2, -d/2, -bf/2, d/2, "Left")
elif shape_type == "Custom":
    st.sidebar.info("Use 'Load Custom' button in Tab 1")

# --- CALCULATION LOGIC ---
has_geom = weld_group.calculate_properties()

# Placeholder for results to be shared across tabs
props = {}
loads_dict = {}
stress_df = pd.DataFrame()
max_force = 0.0
cap = 0.0
dcr = 0.0

if has_geom:
    props = weld_group.properties
    if load_type == "Forces + Coordinates":
        dx, dy, dz = load_x - props['cg_x'], load_y - props['cg_y'], load_z
        M_x_calc = add_Mx + (dy * P_z) - (dz * P_y)
        M_y_calc = add_My + (dz * P_x) - (dx * P_z)
        M_z_calc = add_Mz + (dx * P_y) - (dy * P_x)
    else:
        M_x_calc, M_y_calc, M_z_calc = M_x_input, M_y_input, M_z_input

    loads_dict = {'Px': P_x, 'Py': P_y, 'Pz': P_z, 'Mx': M_x_calc, 'My': M_y_calc, 'Mz': M_z_calc}
    stress_df, max_force = weld_group.calculate_stresses(loads_dict)
    
    cap = phi * 0.6 * F_exx * 0.7071 * provided_size
    dcr = max_force / cap if cap > 0 else 999

# --- TAB 1: 2D DASHBOARD ---
with main_tabs[0]:
    if shape_type == "Custom":
        if 'custom_df' not in st.session_state:
            st.session_state.custom_df = pd.DataFrame({'X1': [0.0], 'Y1': [0.0], 'X2': [5.0], 'Y2': [0.0]})
        edited_df = st.data_editor(st.session_state.custom_df, num_rows="dynamic")
        if st.button("Load Custom Geometry"):
            weld_group = WeldGroup()
            for idx, row in edited_df.iterrows():
                weld_group.add_segment(row['X1'], row['Y1'], row['X2'], row['Y2'], f"Seg {idx+1}")
            st.rerun()

    if has_geom:
        col_res1, col_res2 = st.columns([1, 2])
        
        with col_res2:
            st.subheader("2D Visualization (XY Plane)")
            lines_data = []
            for i, seg in enumerate(weld_group.segments):
                lines_data.append({'x': seg['x1'], 'y': seg['y1'], 'group': f"{seg['label']}-{i}"})
                lines_data.append({'x': seg['x2'], 'y': seg['y2'], 'group': f"{seg['label']}-{i}"})
            
            df_lines = pd.DataFrame(lines_data)
            
            points_data = [{'x': props['cg_x'], 'y': props['cg_y'], 'type': 'Centroid', 'size': 100}]
            if load_type == "Forces + Coordinates":
                points_data.append({'x': load_x, 'y': load_y, 'type': 'Load Point', 'size': 60})
            df_points = pd.DataFrame(points_data)

            chart_lines = alt.Chart(df_lines).mark_line(point=True).encode(
                x=alt.X('x', title='X (in)', scale=alt.Scale(domain=[min(df_lines.x)-5, max(df_lines.x)+5])),
                y=alt.Y('y', title='Y (in)', scale=alt.Scale(domain=[min(df_lines.y)-5, max(df_lines.y)+5])),
                detail='group', color=alt.value('#1f77b4')
            )
            chart_points = alt.Chart(df_points).mark_point(filled=True).encode(
                x='x', y='y', color=alt.Color('type'), size='size', shape='type'
            )
            st.altair_chart((chart_lines + chart_points).interactive(), use_container_width=True)

        with col_res1:
            st.metric("Max Resultant Force", f"{max_force:.3f} k/in")
            st.metric(f"Capacity ({provided_size}\")", f"{cap:.3f} k/in")
            st.metric("Utilization (DCR)", f"{dcr:.3f}", "OK" if dcr <= 1.0 else "FAIL", delta_color="inverse")
            
            st.write("---")
            st.write(f"**Mx:** {loads_dict['Mx']:.2f} k-in")
            st.write(f"**My:** {loads_dict['My']:.2f} k-in")
            st.write(f"**Mz:** {loads_dict['Mz']:.2f} k-in")
    else:
        st.warning("Configure Geometry to see results.")

# --- TAB 2: 3D VISUALIZATION ---
with main_tabs[1]:
    st.header("Interactive 3D View")
    st.caption("Rotate: Left Click + Drag | Pan: Right Click + Drag | Zoom: Scroll")
    
    if has_geom:
        # Prepare Data for PyDeck
        # 1. Weld Lines (Green)
        line_data = []
        for seg in weld_group.segments:
            line_data.append({
                "sourcePosition": [seg['x1'], seg['y1'], 0],
                "targetPosition": [seg['x2'], seg['y2'], 0],
                "name": seg['label']
            })
            
        # 2. Centroid (Red Point)
        point_data = [{
            "position": [props['cg_x'], props['cg_y'], 0],
            "color": [255, 0, 0, 255],
            "radius": 0.2,
            "name": "Centroid"
        }]
        
        # 3. Load Point (Blue Point + Vertical Line)
        if load_type == "Forces + Coordinates":
            point_data.append({
                "position": [load_x, load_y, load_z],
                "color": [0, 0, 255, 255],
                "radius": 0.2,
                "name": "Load Point"
            })
            # Add a vertical drop line to visualize height
            line_data.append({
                "sourcePosition": [load_x, load_y, load_z],
                "targetPosition": [load_x, load_y, 0],
                "name": "Load Height"
            })

        # PyDeck Layers
        layer_lines = pdk.Layer(
            "LineLayer",
            line_data,
            get_source_position="sourcePosition",
            get_target_position="targetPosition",
            get_color=[80, 200, 120], # Emerald Green
            get_width=5,
            pickable=True,
        )
        
        layer_points = pdk.Layer(
            "ScatterplotLayer",
            point_data,
            get_position="position",
            get_color="color",
            get_radius="radius",
            pickable=True,
        )

        # Camera View State
        view_state = pdk.ViewState(
            latitude=0, longitude=0, zoom=3, pitch=45, bearing=30,
            target=[props['cg_x'], props['cg_y'], 0] # Focus on centroid
        )

        r = pdk.Deck(
            layers=[layer_lines, layer_points],
            initial_view_state=view_state,
            tooltip={"text": "{name}"},
            map_style=None # Minimal style
        )
        
        st.pydeck_chart(r)
        
        st.info("The Weld Plane is at Z=0 (Green Lines). The Blue dot is your load application point.")

# --- TAB 3: EXPORT & REPORT ---
with main_tabs[2]:
    st.header("Downloads & Reporting")
    
    if has_geom:
        c1, c2 = st.columns(2)
        
        # 1. CSV Download
        with c1:
            st.subheader("Data Export")
            csv = stress_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Results (CSV)",
                csv,
                "weld_analysis_results.csv",
                "text/csv",
                key='download-csv'
            )
            st.caption("Perfect for opening in Excel.")
            
        # 2. HTML Report Generator
        with c2:
            st.subheader("Printable Report")
            # Generate HTML string
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: sans-serif; padding: 20px; }}
                    h1 {{ color: #2e6c80; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    .pass {{ color: green; font-weight: bold; }}
                    .fail {{ color: red; font-weight: bold; }}
                </style>
            </head>
            <body>
                <h1>Weld Group Analysis Report</h1>
                <hr>
                <h3>1. Input Parameters</h3>
                <ul>
                    <li><b>Loads:</b> Px={P_x}, Py={P_y}, Pz={P_z} (kips)</li>
                    <li><b>Geometry:</b> {shape_type}</li>
                    <li><b>Electrode:</b> E{F_exx}XX</li>
                    <li><b>Leg Size:</b> {provided_size} in</li>
                </ul>
                
                <h3>2. Calculated Properties</h3>
                <ul>
                    <li><b>Centroid:</b> ({props['cg_x']:.3f}, {props['cg_y']:.3f})</li>
                    <li><b>Total Length:</b> {props['L_total']:.2f} in</li>
                    <li><b>Ix:</b> {props['I_x']:.2f} | <b>Iy:</b> {props['I_y']:.2f} | <b>J:</b> {props['J']:.2f}</li>
                </ul>
                
                <h3>3. Results Summary</h3>
                <p><b>Max Force:</b> {max_force:.4f} k/in</p>
                <p><b>Capacity:</b> {cap:.4f} k/in</p>
                <p><b>DCR:</b> <span class="{'pass' if dcr<=1.0 else 'fail'}">{dcr:.3f} ({'OK' if dcr<=1.0 else 'FAIL'})</span></p>
                
                <h3>4. Detailed Stress Table</h3>
                {stress_df.to_html(float_format=lambda x: '{:.3f}'.format(x))}
                
                <br>
                <p><i>Generated by Weld Group Analyzer Pro</i></p>
            </body>
            </html>
            """
            
            st.download_button(
                "📄 Download HTML Report",
                html_content,
                "weld_report.html",
                "text/html"
            )
            st.caption("Download, open in browser, and press Ctrl+P to save as PDF.")

# --- TAB 4: THEORY ---
with main_tabs[3]:
    st.header("Elastic Vector Method")
    st.markdown("Mathematical verification of the logic used in this app.")
    
    st.latex(r"f_{resultant} = \sqrt{(f_{x,dir} + f_{x,tor})^2 + (f_{y,dir} + f_{y,tor})^2 + (f_{z,dir} + f_{z,bend})^2}")
    
    st.markdown("**Components:**")
    st.latex(r"f_{x,dir} = \frac{P_x}{L}, \quad f_{y,dir} = \frac{P_y}{L}, \quad f_{z,dir} = \frac{P_z}{L}")
    st.latex(r"f_{x,tor} = -\frac{M_z \cdot y}{J}, \quad f_{y,tor} = \frac{M_z \cdot x}{J}")
    st.latex(r"f_{z,bend} = \frac{M_x \cdot y}{I_x} - \frac{M_y \cdot x}{I_y}")
