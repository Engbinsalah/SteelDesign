import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# --- CONFIGURATION ---
st.set_page_config(page_title="Weld Group Analyzer", layout="wide")

# --- CLASS DEFINITIONS ---
class WeldGroup:
    def __init__(self):
        self.segments = []
        self.properties = {}
        
    def add_segment(self, x1, y1, x2, y2, label=""):
        length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if length == 0:
            return # Ignore zero length welds
            
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        
        # Moments of inertia of the line segment about its own centroid
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
        
        # Moments of Inertia about Group Centroid
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
                
                # Direct Shear
                fx_direct = loads['Px'] / props['L_total']
                fy_direct = loads['Py'] / props['L_total']
                fz_direct = loads['Pz'] / props['L_total']
                
                # Torsion Mz
                fx_tor = -loads['Mz'] * ry / props['J']
                fy_tor = loads['Mz'] * rx / props['J']
                
                # Bending Mx, My
                fz_mx = loads['Mx'] * ry / props['I_x']
                fz_my = -loads['My'] * rx / props['I_y']
                
                # Totals
                fx_total = fx_direct + fx_tor
                fy_total = fy_direct + fy_tor
                fz_total = fz_direct + fz_mx + fz_my
                
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

st.title("🔩 Elastic Weld Group Analysis")
st.markdown("Calculates capacity using the **Elastic Vector Method**.")

# --- SIDEBAR: INPUTS ---
st.sidebar.header("1. Applied Loads")
load_type = st.sidebar.radio("Load Input Method", ["Forces + Coordinates", "Forces + Direct Moments"])

P_x = st.sidebar.number_input("Px (kips) [Shear X]", value=0.0)
P_y = st.sidebar.number_input("Py (kips) [Shear Y]", value=0.0)
P_z = st.sidebar.number_input("Pz (kips) [Axial Z]", value=0.0)

M_x_input, M_y_input, M_z_input = 0.0, 0.0, 0.0
load_x, load_y, load_z = 0.0, 0.0, 0.0
add_Mx, add_My, add_Mz = 0.0, 0.0, 0.0

if load_type == "Forces + Coordinates":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Load Application Point:**")
    load_x = st.sidebar.number_input("Load X (in)", value=0.0)
    load_y = st.sidebar.number_input("Load Y (in)", value=0.0)
    load_z = st.sidebar.number_input("Load Z (in)", value=0.0)
    
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

# --- MAIN: GEOMETRY ---
st.header("2. Weld Geometry Configuration")

tabs = st.tabs(["Standard Shapes", "Custom Coordinates"])
weld_group = WeldGroup()

with tabs[0]:
    shape_type = st.selectbox("Select Shape", ["Linear", "Rectangle (Box)", "C-Shape", "I/W-Profile"])
    
    if shape_type == "Linear":
        l_len = st.number_input("Length (in)", value=10.0)
        angle = st.number_input("Angle (deg)", value=0.0)
        rad = np.radians(angle)
        weld_group.add_segment(-l_len/2*np.cos(rad), -l_len/2*np.sin(rad), 
                               l_len/2*np.cos(rad), l_len/2*np.sin(rad), "Line")
        
    elif shape_type == "Rectangle (Box)":
        col1, col2 = st.columns(2)
        w = col1.number_input("Width (X) (in)", value=10.0)
        h = col2.number_input("Height (Y) (in)", value=10.0)
        weld_group.add_segment(-w/2, h/2, w/2, h/2, "Top")
        weld_group.add_segment(w/2, h/2, w/2, -h/2, "Right")
        weld_group.add_segment(w/2, -h/2, -w/2, -h/2, "Bottom")
        weld_group.add_segment(-w/2, -h/2, -w/2, h/2, "Left")
        
    elif shape_type == "C-Shape":
        col1, col2 = st.columns(2)
        w = col1.number_input("Web Depth (Y) (in)", value=10.0)
        f = col2.number_input("Flange Width (X) (in)", value=5.0)
        orient = st.selectbox("Direction", ["Right", "Left"])
        if orient == "Right":
            weld_group.add_segment(f, w/2, 0, w/2, "Top")
            weld_group.add_segment(0, w/2, 0, -w/2, "Web")
            weld_group.add_segment(0, -w/2, f, -w/2, "Bot")
        else:
            weld_group.add_segment(-f, w/2, 0, w/2, "Top")
            weld_group.add_segment(0, w/2, 0, -w/2, "Web")
            weld_group.add_segment(0, -w/2, -f, -w/2, "Bot")
            
    elif shape_type == "I/W-Profile":
        col1, col2 = st.columns(2)
        d = col1.number_input("Depth (d) (in)", value=12.0)
        bf = col2.number_input("Flange (bf) (in)", value=6.0)
        pat = st.radio("Pattern", ["All Around", "I-Shape"])
        if pat == "I-Shape":
            weld_group.add_segment(-bf/2, d/2, bf/2, d/2, "Top Flg")
            weld_group.add_segment(-bf/2, -d/2, bf/2, -d/2, "Bot Flg")
            weld_group.add_segment(0, d/2, 0, -d/2, "Web")
        else:
            weld_group.add_segment(-bf/2, d/2, bf/2, d/2, "Top")
            weld_group.add_segment(bf/2, d/2, bf/2, -d/2, "Right")
            weld_group.add_segment(bf/2, -d/2, -bf/2, -d/2, "Bot")
            weld_group.add_segment(-bf/2, -d/2, -bf/2, d/2, "Left")

with tabs[1]:
    if 'custom_df' not in st.session_state:
        st.session_state.custom_df = pd.DataFrame({'X1': [0.0], 'Y1': [0.0], 'X2': [5.0], 'Y2': [0.0]})
    edited_df = st.data_editor(st.session_state.custom_df, num_rows="dynamic")
    if st.button("Load Custom"):
        weld_group = WeldGroup()
        for idx, row in edited_df.iterrows():
            weld_group.add_segment(row['X1'], row['Y1'], row['X2'], row['Y2'], f"Seg {idx+1}")

# --- CALCULATION ---
has_geom = weld_group.calculate_properties()

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
    
    col_res1, col_res2 = st.columns([1, 2])
    
    with col_res2:
        st.subheader("Visualization")
        # Prepare Data for Altair
        lines_data = []
        for i, seg in enumerate(weld_group.segments):
            lines_data.append({'x': seg['x1'], 'y': seg['y1'], 'group': f"Seg{i}"})
            lines_data.append({'x': seg['x2'], 'y': seg['y2'], 'group': f"Seg{i}"})
        
        df_lines = pd.DataFrame(lines_data)
        
        points_data = [{'x': props['cg_x'], 'y': props['cg_y'], 'type': 'Centroid', 'size': 100}]
        if load_type == "Forces + Coordinates":
            points_data.append({'x': load_x, 'y': load_y, 'type': 'Load Point', 'size': 60})
        df_points = pd.DataFrame(points_data)

        # Plot Lines
        chart_lines = alt.Chart(df_lines).mark_line(point=True).encode(
            x=alt.X('x', title='X (in)', scale=alt.Scale(domain=[min(df_lines.x)-5, max(df_lines.x)+5])),
            y=alt.Y('y', title='Y (in)', scale=alt.Scale(domain=[min(df_lines.y)-5, max(df_lines.y)+5])),
            detail='group',
            color=alt.value('blue')
        )

        # Plot Points
        chart_points = alt.Chart(df_points).mark_point(filled=True).encode(
            x='x', y='y',
            color=alt.Color('type', legend=alt.Legend(title="Points")),
            size='size',
            shape='type'
        )

        st.altair_chart((chart_lines + chart_points).interactive(), use_container_width=True)

    with col_res1:
        st.subheader("Properties")
        st.write(f"**Ix:** {props['I_x']:.2f} | **Iy:** {props['I_y']:.2f} | **J:** {props['J']:.2f}")
        st.write(f"**Centroid:** ({props['cg_x']:.2f}, {props['cg_y']:.2f})")
        st.write("---")
        st.write(f"**Mx:** {loads_dict['Mx']:.2f} k-in")
        st.write(f"**My:** {loads_dict['My']:.2f} k-in")
        st.write(f"**Mz:** {loads_dict['Mz']:.2f} k-in")

    # --- CHECK ---
    st.header("3. Results")
    c1, c2, c3 = st.columns(3)
    c1.metric("Max Force", f"{max_force:.3f} k/in")
    
    cap = phi * 0.6 * F_exx * 0.7071 * provided_size
    dcr = max_force / cap if cap > 0 else 999
    c2.metric("Capacity", f"{cap:.3f} k/in")
    c3.metric("DCR", f"{dcr:.3f}", "OK" if dcr <= 1.0 else "FAIL")
    
    st.dataframe(stress_df.style.format("{:.3f}"), use_container_width=True)
else:
    st.warning("Define weld geometry to see results.")
