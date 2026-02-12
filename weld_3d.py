import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
import base64

# --- CONFIGURATION ---
st.set_page_config(page_title="Weld Group Analyzer Pro", layout="wide", page_icon="🏗️")

# --- UTILS FOR REPORTING ---
def plot_to_base64(fig):
    """Converts a matplotlib figure to a base64 string for HTML embedding."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return img_str

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
st.markdown("Calculate capacity, visualize 3D forces, and generate detailed engineering reports.")

# Create Main Tabs
main_tabs = st.tabs(["1. Calculator & 2D", "2. 3D Visualization", "3. Detailed Report"])

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

# Geometry Logic (Same as before)
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
            st.subheader("2D Geometry & Utilization")
            
            # Use Plotly 2D for better interactivity
            fig_2d = go.Figure()

            # Plot Segments (Color coded by approximate stress level if possible, else solid)
            # Simple approach: Plot lines, and markers at ends
            for seg in weld_group.segments:
                fig_2d.add_trace(go.Scatter(
                    x=[seg['x1'], seg['x2']], y=[seg['y1'], seg['y2']],
                    mode='lines+markers', name=seg['label'],
                    line=dict(width=5, color='royalblue')
                ))

            # Centroid
            fig_2d.add_trace(go.Scatter(
                x=[props['cg_x']], y=[props['cg_y']],
                mode='markers', marker=dict(color='red', size=12, symbol='cross'),
                name='Centroid'
            ))

            # Load Point Projection
            if load_type == "Forces + Coordinates":
                fig_2d.add_trace(go.Scatter(
                    x=[load_x], y=[load_y],
                    mode='markers', marker=dict(color='green', size=10, symbol='circle-open'),
                    name='Load (Projected)'
                ))

            fig_2d.update_layout(
                xaxis_title="X (in)", yaxis_title="Y (in)",
                yaxis=dict(scaleanchor="x", scaleratio=1),
                margin=dict(l=0, r=0, t=0, b=0),
                height=400
            )
            st.plotly_chart(fig_2d, use_container_width=True)

        with col_res1:
            st.subheader("Key Results")
            st.metric("Max Force", f"{max_force:.3f} k/in")
            st.metric(f"Capacity ({provided_size}\")", f"{cap:.3f} k/in")
            st.metric("Utilization (DCR)", f"{dcr:.3f}", "OK" if dcr <= 1.0 else "FAIL", delta_color="inverse")
            st.markdown("---")
            st.write(f"**Mx:** {loads_dict['Mx']:.2f} k-in")
            st.write(f"**My:** {loads_dict['My']:.2f} k-in")
            st.write(f"**Mz:** {loads_dict['Mz']:.2f} k-in")

# --- TAB 2: 3D VISUALIZATION (Plotly) ---
with main_tabs[1]:
    st.header("3D Force & Geometry View")
    
    if has_geom:
        fig_3d = go.Figure()

        # 1. Weld Lines (on Z=0 plane)
        for seg in weld_group.segments:
            fig_3d.add_trace(go.Scatter3d(
                x=[seg['x1'], seg['x2']], 
                y=[seg['y1'], seg['y2']], 
                z=[0, 0],
                mode='lines',
                line=dict(color='black', width=6),
                name=f"Weld {seg['label']}"
            ))

        # 2. Centroid
        fig_3d.add_trace(go.Scatter3d(
            x=[props['cg_x']], y=[props['cg_y']], z=[0],
            mode='markers', marker=dict(size=5, color='red'),
            name='Centroid'
        ))

        # 3. Load Point & Force Vectors
        if load_type == "Forces + Coordinates":
            # Load Point Marker
            fig_3d.add_trace(go.Scatter3d(
                x=[load_x], y=[load_y], z=[load_z],
                mode='markers', marker=dict(size=6, color='blue'),
                name='Load Point'
            ))
            
            # Drop line (dashed)
            fig_3d.add_trace(go.Scatter3d(
                x=[load_x, load_x], y=[load_y, load_y], z=[load_z, 0],
                mode='lines', line=dict(color='gray', dash='dash', width=2),
                showlegend=False
            ))

            # FORCE VECTORS (Cones)
            # Scale factor for vectors visualization
            scale = max(props['L_total']/10, 2.0) 

            # Helper to add vector
            def add_vector(u, v, w, color, name):
                if abs(u)+abs(v)+abs(w) > 0.001:
                    fig_3d.add_trace(go.Cone(
                        x=[load_x], y=[load_y], z=[load_z],
                        u=[u], v=[v], w=[w],
                        sizemode="absolute", sizeref=scale,
                        anchor="tail", showscale=False, colorscale=[[0, color], [1, color]],
                        name=name
                    ))

            add_vector(P_x, 0, 0, 'orange', 'Px')
            add_vector(0, P_y, 0, 'green', 'Py')
            add_vector(0, 0, P_z, 'purple', 'Pz')

        # Layout settings
        fig_3d.update_layout(
            scene=dict(
                xaxis_title='X (in)',
                yaxis_title='Y (in)',
                zaxis_title='Z (in)',
                aspectmode='data', # Keeps aspect ratio correct
                camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
            ),
            margin=dict(l=0, r=0, b=0, t=0),
            height=600,
            showlegend=True
        )
        
        st.plotly_chart(fig_3d, use_container_width=True)
        st.info("💡 Interactive 3D View: Click and drag to rotate. Scroll to zoom.")

# --- TAB 3: DETAILED REPORT ---
with main_tabs[2]:
    st.header("Engineering Report Generation")
    
    if has_geom:
        # Generate figures for the report using Matplotlib (Better for static embedding)
        
        # Figure 1: Geometry
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        for seg in weld_group.segments:
            ax1.plot([seg['x1'], seg['x2']], [seg['y1'], seg['y2']], 'b-', linewidth=2)
        ax1.plot(props['cg_x'], props['cg_y'], 'rx', markersize=10, label='Centroid')
        if load_type == "Forces + Coordinates":
            ax1.plot(load_x, load_y, 'go', label='Load Pt')
        ax1.set_title("Weld Group Geometry")
        ax1.set_xlabel("X (in)")
        ax1.set_ylabel("Y (in)")
        ax1.axis('equal')
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend()
        img1 = plot_to_base64(fig1)
        
        # Figure 2: Stress Distribution
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        # Group by segment to get max stress per segment
        seg_max = stress_df.groupby('Segment')['f_res'].max()
        bars = ax2.bar(seg_max.index, seg_max.values, color='orange')
        ax2.axhline(y=cap, color='r', linestyle='--', label='Capacity')
        ax2.set_title("Max Resultant Force per Segment")
        ax2.set_ylabel("Force (k/in)")
        ax2.legend()
        plt.xticks(rotation=45)
        img2 = plot_to_base64(fig2)

        # HTML Content
        report_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #333; }}
                .header {{ border-bottom: 2px solid #005a87; padding-bottom: 10px; margin-bottom: 20px; }}
                h1 {{ color: #005a87; margin: 0; }}
                h2 {{ color: #005a87; font-size: 1.2em; border-left: 5px solid #005a87; padding-left: 10px; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 0.9em; }}
                th {{ background-color: #f2f2f2; text-align: left; padding: 8px; border: 1px solid #ddd; }}
                td {{ padding: 8px; border: 1px solid #ddd; }}
                .status-pass {{ color: green; font-weight: bold; }}
                .status-fail {{ color: red; font-weight: bold; }}
                .grid-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                .img-container {{ text-align: center; margin: 20px 0; border: 1px solid #eee; padding: 10px; }}
                img {{ max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Weld Group Analysis Report</h1>
                <p>Generated by Weld Analyzer Pro | {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>

            <div class="grid-container">
                <div>
                    <h2>1. Design Inputs</h2>
                    <table>
                        <tr><th>Parameter</th><th>Value</th></tr>
                        <tr><td>Shape</td><td>{shape_type}</td></tr>
                        <tr><td>Electrode</td><td>E{F_exx}XX</td></tr>
                        <tr><td>Leg Size</td><td>{provided_size} in</td></tr>
                        <tr><td>Phi Factor</td><td>{phi}</td></tr>
                    </table>
                </div>
                <div>
                    <h2>2. Applied Loads</h2>
                    <table>
                        <tr><th>Force / Moment</th><th>Value</th></tr>
                        <tr><td>Px / Py / Pz</td><td>{P_x} / {P_y} / {P_z} kips</td></tr>
                        <tr><td>Mx (Design)</td><td>{loads_dict['Mx']:.2f} k-in</td></tr>
                        <tr><td>My (Design)</td><td>{loads_dict['My']:.2f} k-in</td></tr>
                        <tr><td>Mz (Design)</td><td>{loads_dict['Mz']:.2f} k-in</td></tr>
                    </table>
                </div>
            </div>

            <h2>3. Section Properties</h2>
            <table>
                <tr>
                    <th>Total Length</th><th>Centroid (X, Y)</th><th>Ix</th><th>Iy</th><th>J</th>
                </tr>
                <tr>
                    <td>{props['L_total']:.2f} in</td>
                    <td>({props['cg_x']:.3f}, {props['cg_y']:.3f})</td>
                    <td>{props['I_x']:.2f} in³</td>
                    <td>{props['I_y']:.2f} in³</td>
                    <td>{props['J']:.2f} in³</td>
                </tr>
            </table>

            <h2>4. Capacity Check</h2>
            <table>
                <tr>
                    <th>Metric</th><th>Value</th><th>Status</th>
                </tr>
                <tr>
                    <td>Max Resultant Force</td>
                    <td>{max_force:.4f} k/in</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td>Weld Capacity</td>
                    <td>{cap:.4f} k/in</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td><b>Demand/Capacity Ratio</b></td>
                    <td><b>{dcr:.3f}</b></td>
                    <td class="{'status-pass' if dcr <= 1.0 else 'status-fail'}">
                        {'OK' if dcr <= 1.0 else 'FAIL'}
                    </td>
                </tr>
            </table>

            <div class="grid-container">
                <div class="img-container">
                    <h3>Geometry Layout</h3>
                    <img src="data:image/png;base64,{img1}" />
                </div>
                <div class="img-container">
                    <h3>Stress Distribution</h3>
                    <img src="data:image/png;base64,{img2}" />
                </div>
            </div>

            <h2>5. Detailed Stresses</h2>
            {stress_df.to_html(index=False, float_format=lambda x: '{:.3f}'.format(x), classes='table')}
            
        </body>
        </html>
        """
        
        st.download_button(
            label="📄 Download Full HTML Report",
            data=report_html,
            file_name="Weld_Analysis_Report.html",
            mime="text/html"
        )
        st.info("Instructions: Download the file, open it in your browser, and select 'Print > Save as PDF' for a PDF version.")

        # Preview the report
        st.markdown("### Report Preview")
        st.components.v1.html(report_html, height=600, scrolling=True)
