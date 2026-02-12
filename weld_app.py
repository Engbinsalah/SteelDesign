import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

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
        # Ix_o = L * (dy)^2 / 12
        # Iy_o = L * (dx)^2 / 12
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
        # Ix = Sum(Ix_o + A*d^2) -> Here Area is Length
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
        # loads = {'Px': 0, 'Py': 0, 'Pz': 0, 'Mx': 0, 'My': 0, 'Mz': 0}
        props = self.properties
        
        results = []
        max_f = 0
        
        for seg in self.segments:
            # Check stress at both start (1) and end (2) of the segment
            for pt_type, x, y in [('Start', seg['x1'], seg['y1']), ('End', seg['x2'], seg['y2'])]:
                # Distance from CG
                rx = x - props['cg_x']
                ry = y - props['cg_y']
                
                # Direct Shear (Force / Total Length)
                fx_direct = loads['Px'] / props['L_total']
                fy_direct = loads['Py'] / props['L_total']
                fz_direct = loads['Pz'] / props['L_total']
                
                # Torsion Mz (in-plane twist) -> Causes x and y shear
                # fx_tor = -Mz * ry / J
                # fy_tor = Mz * rx / J
                fx_tor = -loads['Mz'] * ry / props['J']
                fy_tor = loads['Mz'] * rx / props['J']
                
                # Bending Mx (about X axis) -> Causes z stress (tension/compression)
                # fz_mx = Mx * ry / Ix
                fz_mx = loads['Mx'] * ry / props['I_x']
                
                # Bending My (about Y axis) -> Causes z stress
                # fz_my = -My * rx / Iy
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
st.markdown("""
This tool calculates the capacity of a weld group using the **Elastic Vector Method**. 
Welds are treated as lines (zero thickness). Inputs mimic standard structural engineering workflows.
""")

# --- SIDEBAR: INPUTS ---
st.sidebar.header("1. Applied Loads")
st.sidebar.markdown("Define forces and the location where they are applied.")

load_type = st.sidebar.radio("Load Input Method", ["Forces + Coordinates", "Forces + Direct Moments"])

P_x = st.sidebar.number_input("Px (kips) [Shear X]", value=0.0)
P_y = st.sidebar.number_input("Py (kips) [Shear Y]", value=0.0)
P_z = st.sidebar.number_input("Pz (kips) [Axial Z]", value=0.0)

M_x_input = 0.0
M_y_input = 0.0
M_z_input = 0.0

if load_type == "Forces + Coordinates":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Load Application Point:**")
    load_x = st.sidebar.number_input("Load X (in)", value=0.0)
    load_y = st.sidebar.number_input("Load Y (in)", value=0.0)
    load_z = st.sidebar.number_input("Load Z (in)", value=0.0, help="Distance from weld plane. Positive is usually 'above' the weld.")
    
    st.sidebar.markdown("**Additional Moments (if any):**")
    add_Mx = st.sidebar.number_input("Add'l Mx (k-in)", value=0.0)
    add_My = st.sidebar.number_input("Add'l My (k-in)", value=0.0)
    add_Mz = st.sidebar.number_input("Add'l Mz (k-in)", value=0.0)

else:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Direct Moments at Centroid:**")
    M_x_input = st.sidebar.number_input("Mx (k-in)", value=0.0)
    M_y_input = st.sidebar.number_input("My (k-in)", value=0.0)
    M_z_input = st.sidebar.number_input("Mz (k-in)", value=0.0)

st.sidebar.header("2. Weld Criteria")
F_exx = st.sidebar.selectbox("Electrode Strength", [70, 60, 80, 90, 100], index=0)
phi = st.sidebar.number_input("Phi (Resistance Factor)", value=0.75, help="Usually 0.75 for LRFD")
provided_size = st.sidebar.selectbox("Provided Leg Size (in)", 
                                     [0.1875, 0.25, 0.3125, 0.375, 0.5, 0.625, 0.75], 
                                     index=1, format_func=lambda x: f"{x:.4f} ({int(x*16)}/16)")

# --- MAIN: GEOMETRY ---
st.header("2. Weld Geometry Configuration")

tabs = st.tabs(["Standard Shapes", "Custom Coordinates"])

weld_group = WeldGroup()

with tabs[0]:
    shape_type = st.selectbox("Select Shape", ["Linear", "Rectangle (Box)", "C-Shape", "I/W-Profile"])
    
    if shape_type == "Linear":
        col1, col2 = st.columns(2)
        l_len = col1.number_input("Length (in)", value=10.0)
        angle = col2.number_input("Angle (deg)", value=0.0)
        rad = np.radians(angle)
        # Centered at 0,0 for simplicity
        x1, y1 = - (l_len/2)*np.cos(rad), - (l_len/2)*np.sin(rad)
        x2, y2 = (l_len/2)*np.cos(rad), (l_len/2)*np.sin(rad)
        weld_group.add_segment(x1, y1, x2, y2, "Line")
        
    elif shape_type == "Rectangle (Box)":
        col1, col2 = st.columns(2)
        width = col1.number_input("Width (X-dim) (in)", value=10.0)
        height = col2.number_input("Height (Y-dim) (in)", value=10.0)
        # Top
        weld_group.add_segment(-width/2, height/2, width/2, height/2, "Top")
        # Right
        weld_group.add_segment(width/2, height/2, width/2, -height/2, "Right")
        # Bottom
        weld_group.add_segment(width/2, -height/2, -width/2, -height/2, "Bottom")
        # Left
        weld_group.add_segment(-width/2, -height/2, -width/2, height/2, "Left")
        
    elif shape_type == "C-Shape":
        col1, col2 = st.columns(2)
        width = col1.number_input("Web Depth (Y-dim) (in)", value=10.0)
        flange = col2.number_input("Flange Width (X-dim) (in)", value=5.0)
        orientation = st.selectbox("Opening Direction", ["Right", "Left", "Up", "Down"])
        
        if orientation == "Right": # [
            weld_group.add_segment(flange, width/2, 0, width/2, "Top Flange")
            weld_group.add_segment(0, width/2, 0, -width/2, "Web")
            weld_group.add_segment(0, -width/2, flange, -width/2, "Bot Flange")
        elif orientation == "Left": # ]
            weld_group.add_segment(-flange, width/2, 0, width/2, "Top Flange")
            weld_group.add_segment(0, width/2, 0, -width/2, "Web")
            weld_group.add_segment(0, -width/2, -flange, -width/2, "Bot Flange")
        # Add Up/Down logic if needed
            
    elif shape_type == "I/W-Profile":
        col1, col2 = st.columns(2)
        depth = col1.number_input("Depth (d) (in)", value=12.0)
        bf = col2.number_input("Flange Width (bf) (in)", value=6.0)
        weld_pattern = st.radio("Pattern", ["All Around (Perimeter)", "I-Shape (Flanges + Web)"])
        
        if weld_pattern == "I-Shape (Flanges + Web)":
            # Top Flange
            weld_group.add_segment(-bf/2, depth/2, bf/2, depth/2, "Top Flange")
            # Bot Flange
            weld_group.add_segment(-bf/2, -depth/2, bf/2, -depth/2, "Bot Flange")
            # Web
            weld_group.add_segment(0, depth/2, 0, -depth/2, "Web")
        else:
            # Box perimeter logic roughly
            st.info("Simplification: Modeling outer box perimeter for 'All Around'")
            weld_group.add_segment(-bf/2, depth/2, bf/2, depth/2, "Top")
            weld_group.add_segment(bf/2, depth/2, bf/2, -depth/2, "Right")
            weld_group.add_segment(bf/2, -depth/2, -bf/2, -depth/2, "Bot")
            weld_group.add_segment(-bf/2, -depth/2, -bf/2, depth/2, "Left")

with tabs[1]:
    st.markdown("Enter coordinates for each weld line segment.")
    # Initialize session state for dataframe if not exists
    if 'custom_df' not in st.session_state:
        st.session_state.custom_df = pd.DataFrame(
            {'X1': [0.0], 'Y1': [0.0], 'X2': [5.0], 'Y2': [0.0]}, 
        )
    
    edited_df = st.data_editor(st.session_state.custom_df, num_rows="dynamic")
    
    if st.button("Load Custom Geometry"):
        # Clear existing and load from DF
        weld_group = WeldGroup() # Reset
        for index, row in edited_df.iterrows():
            weld_group.add_segment(row['X1'], row['Y1'], row['X2'], row['Y2'], f"Seg {index+1}")

# --- CALCULATION ---

has_geom = weld_group.calculate_properties()

if has_geom:
    props = weld_group.properties
    
    # Calculate Moments based on inputs
    if load_type == "Forces + Coordinates":
        # M = M_added + Force * distance_to_centroid
        # Lever arms:
        # dx = LoadX - Cgx
        # dy = LoadY - Cgy
        # dz = LoadZ - 0 (assuming weld at Z=0)
        
        dx = load_x - props['cg_x']
        dy = load_y - props['cg_y']
        dz = load_z 
        
        # Mx (about X axis) -> Pz creates moment with dy arm, Py creates moment with dz arm
        # RHR: +My is rotation about Y axis.
        # Mx = Pz*dy - Py*dz
        M_x_calc = add_Mx + (P_z * dy) - (P_y * dz)
        
        # My = Px*dz - Pz*dx
        M_y_calc = add_My + (P_x * dz) - (P_z * dx)
        
        # Mz (Torsion) = Py*dx - Px*dy
        M_z_calc = add_Mz + (P_y * dx) - (P_x * dy)
    else:
        M_x_calc = M_x_input
        M_y_calc = M_y_input
        M_z_calc = M_z_input

    loads_dict = {
        'Px': P_x, 'Py': P_y, 'Pz': P_z,
        'Mx': M_x_calc, 'My': M_y_calc, 'Mz': M_z_calc
    }

    stress_df, max_force = weld_group.calculate_stresses(loads_dict)
    
    # --- VISUALIZATION ---
    col_res1, col_res2 = st.columns([1, 2])
    
    with col_res2:
        st.subheader("Weld Group Visualization")
        fig = go.Figure()
        
        # Draw Segments
        for seg in weld_group.segments:
            fig.add_trace(go.Scatter(
                x=[seg['x1'], seg['x2']], 
                y=[seg['y1'], seg['y2']],
                mode='lines+markers',
                name=seg['label'],
                line=dict(color='blue', width=4)
            ))
            
        # Draw Centroid
        fig.add_trace(go.Scatter(
            x=[props['cg_x']], y=[props['cg_y']],
            mode='markers', marker=dict(color='red', size=12, symbol='cross'),
            name='Centroid'
        ))
        
        # Draw Load Point (if coord mode)
        if load_type == "Forces + Coordinates":
            fig.add_trace(go.Scatter(
                x=[load_x], y=[load_y],
                mode='markers', marker=dict(color='green', size=10, symbol='circle-open'),
                name='Load Point'
            ))

        fig.update_layout(
            xaxis_title="X (in)", yaxis_title="Y (in)",
            axis=dict(scaleanchor="x", scaleratio=1),
            showlegend=True,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_res1:
        st.subheader("Section Properties")
        st.dataframe(pd.DataFrame({
            "Property": ["Total Length", "Centroid X", "Centroid Y", "Ix", "Iy", "J (Polar)"],
            "Value": [
                f"{props['L_total']:.2f} in",
                f"{props['cg_x']:.3f} in",
                f"{props['cg_y']:.3f} in",
                f"{props['I_x']:.2f} in³",
                f"{props['I_y']:.2f} in³",
                f"{props['J']:.2f} in³"
            ]
        }), hide_index=True)
        
        st.subheader("Design Forces")
        st.write(f"**Calculated Moments at Centroid:**")
        st.write(f"Mx = {loads_dict['Mx']:.2f} k-in")
        st.write(f"My = {loads_dict['My']:.2f} k-in")
        st.write(f"Mz = {loads_dict['Mz']:.2f} k-in")

    # --- RESULTS ---
    st.markdown("---")
    st.header("3. Results & Capacity Check")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.metric("Max Resultant Force", f"{max_force:.3f} kips/in")
    
    # Capacity Calc
    # Capacity of 1/16 leg = 0.707 * (1/16) * 0.6 * Fexx
    # Standard engineering often uses simplified factors, but let's do exact per AISC
    # phi * Rn = phi * Fw * Aw
    # Required Effective Throat (te)
    # te_req = Ru / (phi * 0.6 * Fexx)
    
    te_req = max_force / (phi * 0.6 * F_exx)
    leg_req = te_req / 0.7071
    leg_req_16ths = leg_req * 16
    
    with col_b:
        st.metric("Required Leg Size", f"{leg_req:.4f} in", f"{leg_req_16ths:.2f} / 16ths")
        
    with col_c:
        # Check Provided
        capacity_per_inch = phi * 0.6 * F_exx * 0.7071 * provided_size
        dcr = max_force / capacity_per_inch
        
        status = "✅ OK" if dcr <= 1.0 else "❌ FAIL"
        st.metric("Utilization Ratio (DCR)", f"{dcr:.3f}", status)
        st.write(f"Capacity of {provided_size}in leg: {capacity_per_inch:.3f} k/in")

    st.subheader("Detailed Stresses per Segment End")
    st.dataframe(stress_df.style.format("{:.3f}"), use_container_width=True)

else:
    st.warning("Please define at least one valid weld segment.")
