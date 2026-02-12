import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
st.markdown("Calculate capacity, visualize 3D forces, and print detailed reports.")

# Create Main Tabs
main_tabs = st.tabs(["1. Calculator & 2D", "2. 3D Visualization", "3. Print-Ready Report"])

# --- SIDEBAR: INPUTS ---
st.sidebar.header("1. Applied Loads")
load_type = st.sidebar.radio("Load Input Method", ["Forces + Coordinates", "Forces + Direct Moments"])

P_x = st.sidebar.number_input("Px (kips) [Shear X]", value=0.0)
P_y = st.sidebar.number_input("Py (kips) [Shear Y]", value=0.0)
P_z = st.sidebar.number_input("Pz (kips) [Axial Z]", value=0.0)

M_x_calc, M_y_calc, M_z_calc = 0.0, 0.0, 0.0
load_x, load_y, load_z = 0.0, 0.0, 0.0
add_Mx, add_My, add_Mz = 0.0, 0.0, 0.0

if load_type == "Forces + Coordinates":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Load Application Point:**")
    load_x = st.sidebar.number_input("Load X (in)", value=0.0)
    load_y = st.sidebar.number_input("Load Y (in)", value=0.0)
    load_z = st.sidebar.number_input("Load Z (in)", value=10.0, help="Distance from weld plane")
    
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
weld_group = WeldGroup()
shape_type = st.sidebar.selectbox("Geometry Shape", ["Linear", "Rectangle (Box)", "C-Shape", "I/W-Profile", "Custom"])

# Geometry Logic
if shape_type == "Linear":
    l_len = st.sidebar.number_input("Length (in)", value=10.0)
    angle = st.sidebar.number_input("Angle (deg)", value=0.0)
    rad = np.radians(angle)
    weld_group.add_segment(-l_len/2*np.cos(rad), -l_len/2*np.sin(rad), l_len/2*np.cos(rad), l_len/2*np.sin(rad), "Line")
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

# --- CALCULATION LOGIC ---
has_geom = weld_group.calculate_properties()
props, loads_dict, stress_df = {}, {}, pd.DataFrame()
max_force, cap, dcr = 0.0, 0.0, 0.0

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

# --- HELPER: GENERATE FIGURES ---
def get_2d_fig():
    fig = go.Figure()
    for seg in weld_group.segments:
        fig.add_trace(go.Scatter(x=[seg['x1'], seg['x2']], y=[seg['y1'], seg['y2']], mode='lines+markers', line=dict(width=4, color='#1f77b4'), name=seg['label'], showlegend=False))
    fig.add_trace(go.Scatter(x=[props['cg_x']], y=[props['cg_y']], mode='markers', marker=dict(color='red', size=12, symbol='cross'), name='Centroid'))
    if load_type == "Forces + Coordinates":
        fig.add_trace(go.Scatter(x=[load_x], y=[load_y], mode='markers', marker=dict(color='green', size=10, symbol='circle-open'), name='Load Pt'))
    fig.update_layout(xaxis_title="X (in)", yaxis_title="Y (in)", yaxis=dict(scaleanchor="x", scaleratio=1), margin=dict(l=20, r=20, t=30, b=20), height=350, title="Weld Geometry")
    return fig

def get_3d_fig():
    fig = go.Figure()
    # Weld Lines
    for seg in weld_group.segments:
        fig.add_trace(go.Scatter3d(x=[seg['x1'], seg['x2']], y=[seg['y1'], seg['y2']], z=[0, 0], mode='lines', line=dict(color='black', width=6), name=f"Weld"))
    # Centroid
    fig.add_trace(go.Scatter3d(x=[props['cg_x']], y=[props['cg_y']], z=[0], mode='markers', marker=dict(size=5, color='red'), name='Centroid'))
    # Load
    if load_type == "Forces + Coordinates":
        fig.add_trace(go.Scatter3d(x=[load_x], y=[load_y], z=[load_z], mode='markers', marker=dict(size=6, color='blue'), name='Load Point'))
        fig.add_trace(go.Scatter3d(x=[load_x, load_x], y=[load_y, load_y], z=[load_z, 0], mode='lines', line=dict(color='gray', dash='dash', width=2), showlegend=False))
        # Force Vectors
        scale = max(props['L_total']/8, 1.0)
        if abs(P_x) > 0.01: fig.add_trace(go.Cone(x=[load_x], y=[load_y], z=[load_z], u=[P_x], v=[0], w=[0], sizemode="absolute", sizeref=scale, anchor="tail", colorscale=[[0, 'orange'],[1,'orange']], showscale=False, name='Px'))
        if abs(P_y) > 0.01: fig.add_trace(go.Cone(x=[load_x], y=[load_y], z=[load_z], u=[0], v=[P_y], w=[0], sizemode="absolute", sizeref=scale, anchor="tail", colorscale=[[0, 'green'],[1,'green']], showscale=False, name='Py'))
        if abs(P_z) > 0.01: fig.add_trace(go.Cone(x=[load_x], y=[load_y], z=[load_z], u=[0], v=[0], w=[P_z], sizemode="absolute", sizeref=scale, anchor="tail", colorscale=[[0, 'purple'],[1,'purple']], showscale=False, name='Pz'))

    fig.update_layout(scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z', aspectmode='data'), margin=dict(l=0, r=0, b=0, t=0), height=500)
    return fig

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
            st.plotly_chart(get_2d_fig(), use_container_width=True)
        with col_res1:
            st.subheader("Results")
            st.metric("Max Resultant Force", f"{max_force:.3f} k/in")
            st.metric(f"Capacity ({provided_size}\")", f"{cap:.3f} k/in")
            st.metric("Utilization (DCR)", f"{dcr:.3f}", "OK" if dcr <= 1.0 else "FAIL", delta_color="inverse")
            st.markdown("---")
            st.write(f"**Mx:** {loads_dict['Mx']:.2f} k-in")
            st.write(f"**My:** {loads_dict['My']:.2f} k-in")
            st.write(f"**Mz:** {loads_dict['Mz']:.2f} k-in")
    else:
        st.warning("Configure Geometry to see results.")

# --- TAB 2: 3D VISUALIZATION ---
with main_tabs[1]:
    st.header("3D Force & Geometry View")
    if has_geom:
        st.plotly_chart(get_3d_fig(), use_container_width=True)
        st.info("Left Click: Rotate | Right Click: Pan | Scroll: Zoom")

# --- TAB 3: PRINT-READY REPORT ---
with main_tabs[2]:
    if has_geom:
        st.markdown("### 🖨️ Instructions: Press `Ctrl + P` (or Cmd + P) to Save as PDF")
        st.divider()
        
        # Report Header
        st.markdown(f"## Weld Group Analysis Report")
        st.markdown(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 1. Design Inputs")
            st.write(f"- **Shape:** {shape_type}")
            st.write(f"- **Electrode:** E{F_exx}XX")
            st.write(f"- **Leg Size:** {provided_size} in")
            st.write(f"- **Phi:** {phi}")
        with c2:
            st.markdown("#### 2. Applied Loads")
            st.write(f"- **Forces:** Px={P_x}, Py={P_y}, Pz={P_z} (k)")
            st.write(f"- **Design Mx:** {loads_dict['Mx']:.2f} k-in")
            st.write(f"- **Design My:** {loads_dict['My']:.2f} k-in")
            st.write(f"- **Design Mz:** {loads_dict['Mz']:.2f} k-in")

        st.markdown("#### 3. Section Properties")
        prop_df = pd.DataFrame([{
            "L_total": f"{props['L_total']:.2f}",
            "Centroid": f"({props['cg_x']:.2f}, {props['cg_y']:.2f})",
            "Ix": f"{props['I_x']:.2f}", "Iy": f"{props['I_y']:.2f}", "J": f"{props['J']:.2f}"
        }])
        st.dataframe(prop_df, hide_index=True)

        st.markdown("#### 4. Capacity Check")
        res_df = pd.DataFrame([{
            "Max Force (k/in)": f"{max_force:.4f}",
            "Capacity (k/in)": f"{cap:.4f}",
            "DCR": f"{dcr:.3f}",
            "Status": "✅ OK" if dcr <= 1.0 else "❌ FAIL"
        }])
        st.dataframe(res_df, hide_index=True)

        st.markdown("#### 5. Geometry Plot")
        # Display the 2D figure statically
        st.plotly_chart(get_2d_fig(), key="report_2d", use_container_width=True)
        
        st.markdown("#### 6. Detailed Stresses")
        # Format columns for display
        fmt_cols = ['X', 'Y', 'fx', 'fy', 'fz', 'f_res']
        st.dataframe(stress_df.style.format({c: "{:.3f}" for c in fmt_cols}), use_container_width=True)
