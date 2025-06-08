import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from enum import Enum

class MaterialType(Enum):
    """Predefined material types for quick reference"""
    CARBON_T300 = {
        'E11': 138,  # GPa
        'E22': 9,
        'nu12': 0.3,
        'G12': 6.9,
        'density': 1600  # kg/m³
    }
    GLASS_E = {
        'E11': 45,
        'E22': 12,
        'nu12': 0.3,
        'G12': 5.5,
        'density': 2000
    }
    KEVLAR_49 = {
        'E11': 76,
        'E22': 5.5,
        'nu12': 0.34,
        'G12': 2.1,
        'density': 1440
    }


@dataclass
class PlyProperties:
    """Properties for a single ply"""
    E11: float  # Longitudinal modulus (GPa)
    E22: float  # Transverse modulus (GPa)
    nu12: float  # Major Poisson's ratio
    G12: float  # In-plane shear modulus (GPa)
    thickness: float  # Ply thickness (mm)
    orientation: float  # Fiber orientation angle (degrees)
    density: float  # Density (kg/m³)
    name: str = ""  # Optional name/identifier for the ply
    
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
    
    @classmethod
    def from_material_type(cls, material_type: MaterialType, thickness: float, orientation: float, name: str = "") -> 'PlyProperties':
        """Create ply properties from a predefined material type"""
        props = material_type.value
        return cls(
            E11=props['E11'],
            E22=props['E22'],
            nu12=props['nu12'],
            G12=props['G12'],
            thickness=thickness,
            orientation=orientation,
            density=props['density'],
            name=name
        )

class CustomLayup:
    def __init__(self, plies: List[PlyProperties]):
        """
        Initialize a custom layup with any number of plies
        
        Args:
            plies: List of PlyProperties objects, each defining a layer
        """
        self.plies = plies
        self.total_thickness = sum(ply.thickness for ply in plies)
        self._validate_layup()
    
    def _validate_layup(self):
        """Validate the layup configuration"""
        if not self.plies:
            raise ValueError("Layup must contain at least one ply")
        if any(ply.thickness <= 0 for ply in self.plies):
            raise ValueError("All ply thicknesses must be positive")
    
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
        
        # Extract the in-plane compliance terms
        S11 = S[0,0]
        S12 = S[0,1]
        S22 = S[1,1]
        S66 = S[2,2]
        
        # Calculate effective properties
        E_x = 1 / (h * S11)
        E_y = 1 / (h * S22)
        nu_xy = -S12 / S11
        G_xy = 1 / (h * S66)
        
        # Calculate average density
        avg_density = sum(ply.density * ply.thickness for ply in self.plies) / self.total_thickness
        
        return {
            'E_x': E_x / 1e9,  # Convert back to GPa
            'E_y': E_y / 1e9,
            'nu_xy': nu_xy,
            'G_xy': G_xy / 1e9,
            'thickness': self.total_thickness * 1000,  # Convert to mm
            'density': avg_density,
            'mass_per_area': avg_density * self.total_thickness  # kg/m²
        }
    
    def get_ply_stresses(self, loads: Dict[str, float]) -> List[Dict[str, np.ndarray]]:
        """
        Calculate stresses in each ply for given loads
        
        Args:
            loads: Dictionary of loads (Nx, Ny, Nxy, Mx, My, Mxy)
        
        Returns:
            List of dictionaries containing stresses for each ply
        """
        A, B, D = self.calculate_ABD_matrices()
        ABD = np.block([[A, B], [B, D]])
        
        # Create load vector
        N = np.array([loads.get('Nx', 0), loads.get('Ny', 0), loads.get('Nxy', 0)])
        M = np.array([loads.get('Mx', 0), loads.get('My', 0), loads.get('Mxy', 0)])
        load_vector = np.concatenate([N, M])
        
        # Calculate mid-plane strains and curvatures
        strains_curvatures = np.linalg.solve(ABD, load_vector)
        epsilon0 = strains_curvatures[:3]
        kappa = strains_curvatures[3:]
        
        # Calculate stresses in each ply
        z_bottom = -self.total_thickness / 2
        ply_stresses = []
        
        for ply in self.plies:
            z_top = z_bottom + ply.thickness
            z_mid = (z_top + z_bottom) / 2
            
            # Calculate strain at mid-plane of ply
            epsilon = epsilon0 + z_mid * kappa
            
            # Transform strain to material coordinates
            T = self._get_T_matrix(ply.orientation)
            epsilon_material = T @ epsilon
            
            # Calculate stress in material coordinates
            Q = self._get_Q_matrix(ply)
            sigma_material = Q @ epsilon_material
            
            # Transform stress back to global coordinates
            T_inv = np.linalg.inv(T)
            sigma_global = T_inv @ sigma_material
            
            ply_stresses.append({
                'ply_name': ply.name or f"Ply {len(ply_stresses) + 1}",
                'z_location': z_mid * 1000,  # Convert to mm
                'strain_material': epsilon_material,
                'strain_global': epsilon,
                'stress_material': sigma_material / 1e6,  # Convert to MPa
                'stress_global': sigma_global / 1e6
            })
            
            z_bottom = z_top
        
        return ply_stresses

def create_layup_from_sequence(sequence: List[Dict]) -> CustomLayup:
    """
    Create a layup from a sequence of ply definitions
    
    Args:
        sequence: List of dictionaries, each defining a ply with:
            - material_type: MaterialType enum or dict of properties
            - thickness: float (mm)
            - orientation: float (degrees)
            - name: str (optional)
    
    Returns:
        CustomLayup object
    """
    plies = []
    
    for ply_def in sequence:
        if isinstance(ply_def['material_type'], MaterialType):
            ply = PlyProperties.from_material_type(
                material_type=ply_def['material_type'],
                thickness=ply_def['thickness'],
                orientation=ply_def['orientation'],
                name=ply_def.get('name', '')
            )
        else:
            # Custom material properties
            ply = PlyProperties(
                E11=ply_def['material_type']['E11'],
                E22=ply_def['material_type']['E22'],
                nu12=ply_def['material_type']['nu12'],
                G12=ply_def['material_type']['G12'],
                thickness=ply_def['thickness'],
                orientation=ply_def['orientation'],
                density=ply_def['material_type'].get('density', 1600),
                name=ply_def.get('name', '')
            )
        plies.append(ply)
    
    return CustomLayup(plies)

if __name__ == "__main__":
    # Example 1: Using predefined materials
    sequence1 = [
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 0, 'name': 'Carbon 0°'},
        {'material_type': MaterialType.GLASS_E, 'thickness': 0.2, 'orientation': 45, 'name': 'Glass 45°'},
        {'material_type': MaterialType.KEVLAR_49, 'thickness': 0.15, 'orientation': -45, 'name': 'Kevlar -45°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 90, 'name': 'Carbon 90°'}
    ]
    
    layup1 = create_layup_from_sequence(sequence1)
    
    # Example 2: Using custom materials
    custom_material = {
        'E11': 200,  # GPa
        'E22': 8,
        'nu12': 0.3,
        'G12': 5,
        'density': 1800
    }
    
    sequence2 = [
        {'material_type': custom_material, 'thickness': 0.1, 'orientation': 0, 'name': 'Custom 0°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 45, 'name': 'Carbon 45°'},
        {'material_type': custom_material, 'thickness': 0.1, 'orientation': -45, 'name': 'Custom -45°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 90, 'name': 'Carbon 90°'}
    ]
    
    layup2 = create_layup_from_sequence(sequence2)

    sequence3 = [
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 0, 'name': 'Carbon 0°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 45, 'name': 'Carbon 45°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': -45, 'name': 'Carbon -45°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 0, 'name': 'Carbon 0°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 0, 'name': 'Carbon 0°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': -45, 'name': 'Carbon -45°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 45, 'name': 'Carbon 45°'},
        {'material_type': MaterialType.CARBON_T300, 'thickness': 0.1, 'orientation': 0, 'name': 'Carbon 0°'}
    ]
    
    layup3 = create_layup_from_sequence(sequence3)
    
    # Print results for both layups
    for i, layup in enumerate([layup1, layup2, layup3], 1):
        print(f"\nLayup {i} Properties:")
        props = layup.calculate_effective_properties()
        for key, value in props.items():
            print(f"{key}: {value:.3f}")
        
        # Example stress analysis
        loads = {
            'Nx': 1000,  # N/m
            'Ny': 0,
            'Nxy': 0,
            'Mx': 0,
            'My': 0,
            'Mxy': 0
        }
        
        stresses = layup.get_ply_stresses(loads)
        print(f"\nLayup {i} Ply Stresses (MPa):")
        for ply in stresses:
            print(f"\n{ply['ply_name']} at z = {ply['z_location']:.2f} mm:")
            print(f"Global stresses: σx = {ply['stress_global'][0]:.1f}, σy = {ply['stress_global'][1]:.1f}, τxy = {ply['stress_global'][2]:.1f}")
            print(f"Material stresses: σ1 = {ply['stress_material'][0]:.1f}, σ2 = {ply['stress_material'][1]:.1f}, τ12 = {ply['stress_material'][2]:.1f}") 