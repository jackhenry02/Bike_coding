import numpy as np
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class PlyProperties:
    E11: float  # Longitudinal modulus (GPa)
    E22: float  # Transverse modulus (GPa)
    nu12: float  # Major Poisson's ratio
    G12: float  # In-plane shear modulus (GPa)
    thickness: float  # Ply thickness (mm)
    orientation: float  # Fiber orientation angle (degrees)
    
    def __post_init__(self):
        # Convert GPa to Pa for internal calculations
        self.E11 *= 1e9
        self.E22 *= 1e9
        self.G12 *= 1e9
        # Convert thickness to meters
        self.thickness *= 1e-3
        
    @property
    def nu21(self) -> float:
        """Calculate minor Poisson's ratio"""
        return self.nu12 * self.E22 / self.E11

class CompositeLayup:
    def __init__(self, plies: List[PlyProperties]):
        self.plies = plies
        self.total_thickness = sum(ply.thickness for ply in plies)
        
    def _get_Q_matrix(self, ply: PlyProperties) -> np.ndarray:
        """Calculate the reduced stiffness matrix Q for a ply"""
        Q11 = ply.E11 / (1 - ply.nu12 * ply.nu21)
        Q22 = ply.E22 / (1 - ply.nu12 * ply.nu21)
        Q12 = ply.nu12 * ply.E22 / (1 - ply.nu12 * ply.nu21)
        Q66 = ply.G12
        
        return np.array([
            [Q11, Q12, 0],
            [Q12, Q22, 0],
            [0, 0, Q66]
        ])
    
    def _get_T_matrix(self, theta: float) -> np.ndarray:
        """Calculate the transformation matrix T for a given angle"""
        theta_rad = np.radians(theta)
        c = np.cos(theta_rad)
        s = np.sin(theta_rad)
        
        return np.array([
            [c**2, s**2, 2*c*s],
            [s**2, c**2, -2*c*s],
            [-c*s, c*s, c**2 - s**2]
        ])
    
    def _get_Q_bar_matrix(self, ply: PlyProperties) -> np.ndarray:
        """Calculate the transformed reduced stiffness matrix Q_bar for a ply"""
        Q = self._get_Q_matrix(ply)
        T = self._get_T_matrix(ply.orientation)
        T_inv = np.linalg.inv(T)
        
        return T_inv @ Q @ T
    
    def calculate_ABD_matrices(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate the A, B, and D matrices for the laminate"""
        A = np.zeros((3, 3))
        B = np.zeros((3, 3))
        D = np.zeros((3, 3))
        
        z_bottom = -self.total_thickness / 2
        
        for ply in self.plies:
            Q_bar = self._get_Q_bar_matrix(ply)
            z_top = z_bottom + ply.thickness
            z_mid = (z_top + z_bottom) / 2
            
            A += Q_bar * ply.thickness
            B += Q_bar * (z_top**2 - z_bottom**2) / 2
            D += Q_bar * (z_top**3 - z_bottom**3) / 3
            
            z_bottom = z_top
        
        return A, B, D
    
    def calculate_effective_properties(self) -> dict:
        """Calculate the effective engineering properties of the laminate"""
        A, B, D = self.calculate_ABD_matrices()
        h = self.total_thickness
        
        # Create the full ABD matrix
        ABD = np.block([
            [A, B],
            [B, D]
        ])
        
        # Calculate compliance matrix
        S = np.linalg.inv(ABD)
        
        # For unsymmetric laminates, use compliance matrix approach
        # Extract the in-plane compliance terms (S11, S12, S22, S66)
        S11 = S[0,0]
        S12 = S[0,1]
        S22 = S[1,1]
        S66 = S[2,2]
        
        # Calculate effective properties using compliance matrix
        E_x = 1 / (h * S11)
        E_y = 1 / (h * S22)
        nu_xy = -S12 / S11
        G_xy = 1 / (h * S66)
        
        return {
            'E_x': E_x / 1e9,  # Convert back to GPa
            'E_y': E_y / 1e9,
            'nu_xy': nu_xy,
            'G_xy': G_xy / 1e9,
            'thickness': self.total_thickness * 1000,  # Convert to mm
            'density': sum(ply.thickness for ply in self.plies) / self.total_thickness  # Assuming uniform density
        }

def create_symmetric_layup(ply_properties: PlyProperties, orientations: List[float]) -> CompositeLayup:
    """Create a symmetric layup from a list of orientations"""
    plies = []
    # Add plies for first half
    for angle in orientations:
        plies.append(PlyProperties(
            E11=ply_properties.E11/1e9,  # Convert back to GPa for input
            E22=ply_properties.E22/1e9,
            nu12=ply_properties.nu12,
            G12=ply_properties.G12/1e9,
            thickness=ply_properties.thickness*1000,  # Convert back to mm
            orientation=angle
        ))
    # Add plies for second half (mirrored)
    for angle in reversed(orientations):
        plies.append(PlyProperties(
            E11=ply_properties.E11/1e9,
            E22=ply_properties.E22/1e9,
            nu12=ply_properties.nu12,
            G12=ply_properties.G12/1e9,
            thickness=ply_properties.thickness*1000,
            orientation=angle
        ))
    return CompositeLayup(plies)

if __name__ == "__main__":
    # Example ply properties (Carbon Fiber)
    ply_props = PlyProperties(
        E11=138,  # GPa
        E22=9,    # GPa
        nu12=0.3,
        G12=6.9,  # GPa
        thickness=0.1,  # mm
        orientation=0  # degrees (will be set in layup)
    )
    
    # Create symmetric layup [0, 45, -45, 0]s
    orientations = [0, 45, -45, 0]
    layup = create_symmetric_layup(ply_props, orientations)
    
    # Calculate and print effective properties
    effective_props = layup.calculate_effective_properties()
    print("\nEffective Laminate Properties:")
    print(f"E_x: {effective_props['E_x']:.2f} GPa")
    print(f"E_y: {effective_props['E_y']:.2f} GPa")
    print(f"nu_xy: {effective_props['nu_xy']:.3f}")
    print(f"G_xy: {effective_props['G_xy']:.2f} GPa")
    print(f"Total thickness: {effective_props['thickness']:.2f} mm")
    
    # Print ABD matrices
    A, B, D = layup.calculate_ABD_matrices()
    print("\nA matrix (N/m):")
    print(A/1e6)  # Convert to MN/m for readability
    print("\nB matrix (N):")
    print(B/1e3)  # Convert to kN for readability
    print("\nD matrix (N·m):")
    print(D)  # Keep in N·m 