import numpy as np
from composipy import OrthotropicMaterial, LaminateProperty, LaminateStrength
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class PlyProperties:
    E11: float  # Longitudinal modulus (GPa)
    E22: float  # Transverse modulus (GPa)
    nu12: float  # Major Poisson's ratio
    G12: float  # In-plane shear modulus (GPa)
    thickness: float  # Ply thickness (mm)
    orientation: float  # Fiber orientation angle (degrees)
    density: float = 1600  # Density (kg/m³)

class CompositeAnalysis:
    def __init__(self, plies: List[PlyProperties]):
        self.plies = plies
        self.total_thickness = sum(ply.thickness for ply in plies)
        
        # Create composipy materials and laminate
        self.materials = self._create_materials()
        self.laminate = self._create_laminate()
    
    def _create_materials(self) -> List[OrthotropicMaterial]:
        """Create OrthotropicMaterial objects for each ply"""
        materials = []
        for ply in self.plies:
            # Convert to composipy material format
            materials.append(OrthotropicMaterial(
                e1=ply.E11 * 1e9,  # Convert to Pa
                e2=ply.E22 * 1e9,
                v12=ply.nu12,
                g12=ply.G12 * 1e9,
                thickness=ply.thickness * 1e-3,  # Convert to m
                theta=ply.orientation
            ))
        return materials
    
    def _create_laminate(self) -> LaminateProperty:
        """Create a LaminateProperty object"""
        return LaminateProperty(self.materials)
    
    def calculate_effective_properties(self) -> Dict[str, float]:
        """Calculate effective properties using composipy"""
        props = self.laminate.get_effective_properties()
        
        return {
            'E_x': props['Ex'] / 1e9,  # Convert back to GPa
            'E_y': props['Ey'] / 1e9,
            'nu_xy': props['nuxy'],
            'G_xy': props['Gxy'] / 1e9,
            'thickness': self.total_thickness,
            'density': self.plies[0].density  # Assuming uniform density
        }
    
    def calculate_stress_strain(self, loads: Dict[str, float]) -> Dict[str, np.ndarray]:
        """Calculate stress and strain distribution through thickness"""
        # Convert loads to composipy format
        N = np.array([loads.get('Nx', 0), loads.get('Ny', 0), loads.get('Nxy', 0)])
        M = np.array([loads.get('Mx', 0), loads.get('My', 0), loads.get('Mxy', 0)])
        
        # Get stress and strain from composipy
        stresses, strains = self.laminate.get_stress_strain(N, M)
        
        return {
            'stresses': stresses,  # Through-thickness stress distribution
            'strains': strains,    # Through-thickness strain distribution
            'max_stress': np.max(np.abs(stresses), axis=0),  # Maximum stresses
            'max_strain': np.max(np.abs(strains), axis=0)    # Maximum strains
        }
    
    def calculate_failure(self, loads: Dict[str, float], criterion: str = 'tsai_hill') -> Dict[str, float]:
        """Calculate failure indices using various criteria"""
        # Get stress distribution
        stress_strain = self.calculate_stress_strain(loads)
        stresses = stress_strain['stresses']
        
        # Create LaminateStrength object for failure analysis
        strength = LaminateStrength(self.materials, stresses)
        
        # Calculate failure indices
        if criterion == 'tsai_hill':
            failure_indices = strength.tsai_hill()
        elif criterion == 'max_stress':
            failure_indices = strength.max_stress()
        elif criterion == 'max_strain':
            failure_indices = strength.max_strain()
        else:
            raise ValueError(f"Unknown failure criterion: {criterion}")
        
        return {
            'max_failure_index': np.max(failure_indices),
            'failure_indices': failure_indices,
            'failed_plies': np.where(failure_indices >= 1.0)[0].tolist()
        }

def create_symmetric_layup(ply_properties: PlyProperties, orientations: List[float]) -> CompositeAnalysis:
    """Create a symmetric layup from a list of orientations"""
    plies = []
    # Add plies for first half
    for angle in orientations:
        plies.append(PlyProperties(
            E11=ply_properties.E11,
            E22=ply_properties.E22,
            nu12=ply_properties.nu12,
            G12=ply_properties.G12,
            thickness=ply_properties.thickness,
            orientation=angle,
            density=ply_properties.density
        ))
    # Add plies for second half (mirrored)
    for angle in reversed(orientations):
        plies.append(PlyProperties(
            E11=ply_properties.E11,
            E22=ply_properties.E22,
            nu12=ply_properties.nu12,
            G12=ply_properties.G12,
            thickness=ply_properties.thickness,
            orientation=angle,
            density=ply_properties.density
        ))
    return CompositeAnalysis(plies)

if __name__ == "__main__":
    # Example usage
    ply_props = PlyProperties(
        E11=138,  # GPa
        E22=9,    # GPa
        nu12=0.3,
        G12=6.9,  # GPa
        thickness=0.1,  # mm
        orientation=0,  # degrees
        density=1600  # kg/m³
    )
    
    # Create symmetric layup [0, 45, -45, 0]s
    orientations = [0, 45, -45, 0]
    layup = create_symmetric_layup(ply_props, orientations)
    
    # Calculate effective properties
    effective_props = layup.calculate_effective_properties()
    print("\nEffective Laminate Properties:")
    for key, value in effective_props.items():
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
    
    stress_strain = layup.calculate_stress_strain(loads)
    print("\nMaximum Stresses (MPa):")
    print(f"σx: {stress_strain['max_stress'][0]/1e6:.2f}")
    print(f"σy: {stress_strain['max_stress'][1]/1e6:.2f}")
    print(f"τxy: {stress_strain['max_stress'][2]/1e6:.2f}")
    
    # Example failure analysis
    failure = layup.calculate_failure(loads)
    print("\nFailure Analysis:")
    print(f"Maximum Failure Index: {failure['max_failure_index']:.3f}")
    if failure['failed_plies']:
        print(f"Failed Plies: {failure['failed_plies']}")
    else:
        print("No ply failures predicted") 