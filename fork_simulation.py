import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class MaterialProperties:
    # Basic material properties
    E_axial: float  # Young's modulus in axial direction (GPa)
    E_transverse: float  # Young's modulus in transverse direction (GPa)
    G: float  # Shear modulus (GPa)
    nu: float  # Poisson's ratio
    rho: float  # Density (kg/m³)
    cost_per_kg: float  # Cost per kg (£)
    
    # Damping properties
    damping_ratio: float  # Damping ratio (ζ)
    
    def __post_init__(self):
        # Convert GPa to Pa for internal calculations
        self.E_axial *= 1e9
        self.E_transverse *= 1e9
        self.G *= 1e9

@dataclass
class ForkGeometry:
    length: float  # Length of fork (m)
    outer_diameter: float  # Outer diameter (m)
    wall_thickness: float  # Wall thickness (m)
    
    @property
    def inner_diameter(self) -> float:
        return self.outer_diameter - 2 * self.wall_thickness
    
    @property
    def cross_sectional_area(self) -> float:
        return np.pi * (self.outer_diameter**2 - self.inner_diameter**2) / 4
    
    @property
    def moment_of_inertia(self) -> float:
        return np.pi * (self.outer_diameter**4 - self.inner_diameter**4) / 64
    
    @property
    def volume(self) -> float:
        return self.cross_sectional_area * self.length

class ForkSimulation:
    def __init__(self, material: MaterialProperties, geometry: ForkGeometry):
        self.material = material
        self.geometry = geometry
        
    @property
    def mass(self) -> float:
        return self.geometry.volume * self.material.rho
    
    @property
    def cost(self) -> float:
        return self.mass * self.material.cost_per_kg
    
    def axial_stress(self, axial_force: float) -> float:
        """Calculate axial stress under given force"""
        return axial_force / self.geometry.cross_sectional_area
    
    def bending_stress(self, transverse_force: float, distance_from_base: float) -> float:
        """Calculate bending stress at given distance from base"""
        moment = transverse_force * distance_from_base
        return (moment * self.geometry.outer_diameter/2) / self.geometry.moment_of_inertia
    
    def natural_frequency(self, mode: int = 1) -> float:
        """Calculate natural frequency for given mode"""
        # Using Euler-Bernoulli beam theory
        L = self.geometry.length
        E = self.material.E_axial
        I = self.geometry.moment_of_inertia
        m = self.mass / L  # mass per unit length
        
        # Mode shape coefficients
        beta_L = {1: 1.875, 2: 4.694, 3: 7.855}[mode]
        
        return (beta_L**2 / (2 * np.pi * L**2)) * np.sqrt(E * I / m)
    
    def damping_coefficient(self) -> float:
        """Calculate damping coefficient"""
        return 2 * self.material.damping_ratio * np.sqrt(self.material.E_axial * self.geometry.moment_of_inertia * self.mass)
    
    def plot_stress_distribution(self, axial_force: float, transverse_force: float):
        """Plot stress distribution along the fork"""
        x = np.linspace(0, self.geometry.length, 100)
        axial_stress = np.full_like(x, self.axial_stress(axial_force))
        bending_stress = self.bending_stress(transverse_force, x)
        total_stress = axial_stress + bending_stress
        
        plt.figure(figsize=(10, 6))
        plt.plot(x, axial_stress/1e6, label='Axial Stress')
        plt.plot(x, bending_stress/1e6, label='Bending Stress')
        plt.plot(x, total_stress/1e6, label='Total Stress')
        plt.xlabel('Distance from base (m)')
        plt.ylabel('Stress (MPa)')
        plt.title('Stress Distribution Along Fork')
        plt.legend()
        plt.grid(True)
        plt.show()
    
    def plot_frequency_response(self, force_amplitude: float, frequency_range: Tuple[float, float]):
        """Plot frequency response of the fork"""
        freq = np.linspace(frequency_range[0], frequency_range[1], 1000)
        omega = 2 * np.pi * freq
        omega_n = 2 * np.pi * self.natural_frequency()
        c = self.damping_coefficient()
        k = self.material.E_axial * self.geometry.moment_of_inertia / self.geometry.length**3
        
        # Frequency response function
        H = 1 / (k - self.mass * omega**2 + 1j * c * omega)
        response = np.abs(H) * force_amplitude
        
        plt.figure(figsize=(10, 6))
        plt.plot(freq, response * 1000)  # Convert to mm
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Amplitude (mm)')
        plt.title('Frequency Response')
        plt.grid(True)
        plt.show()

    def plot_steady_state_vibration(self, force_amplitude: float, frequency: float, duration: float = 2.0):
        """Plot steady-state vibration response to a sinusoidal force"""
        t = np.linspace(0, duration, 1000)
        omega = 2 * np.pi * frequency
        omega_n = 2 * np.pi * self.natural_frequency()
        c = self.damping_coefficient()
        k = self.material.E_axial * self.geometry.moment_of_inertia / self.geometry.length**3
        
        # Steady-state response
        H = 1 / (k - self.mass * omega**2 + 1j * c * omega)
        phase = np.angle(H)
        amplitude = np.abs(H) * force_amplitude
        
        # Input force and response
        force = force_amplitude * np.sin(omega * t)
        response = amplitude * np.sin(omega * t + phase)
        
        plt.figure(figsize=(12, 8))
        plt.subplot(2, 1, 1)
        plt.plot(t, force, label='Input Force')
        plt.xlabel('Time (s)')
        plt.ylabel('Force (N)')
        plt.title('Input Force')
        plt.grid(True)
        plt.legend()
        
        plt.subplot(2, 1, 2)
        plt.plot(t, response * 1000, label='Response')  # Convert to mm
        plt.xlabel('Time (s)')
        plt.ylabel('Displacement (mm)')
        plt.title('Steady-State Response')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        plt.show()

    def plot_step_response(self, force_amplitude: float, duration: float = 2.0):
        """Plot step response of the fork to a sudden force application"""
        t = np.linspace(0, duration, 1000)
        omega_n = 2 * np.pi * self.natural_frequency()
        zeta = self.material.damping_ratio
        c = self.damping_coefficient()
        k = self.material.E_axial * self.geometry.moment_of_inertia / self.geometry.length**3
        
        # Step response for underdamped system (zeta < 1)
        if zeta < 1:
            omega_d = omega_n * np.sqrt(1 - zeta**2)
            response = (force_amplitude/k) * (1 - np.exp(-zeta * omega_n * t) * 
                    (np.cos(omega_d * t) + (zeta * omega_n/omega_d) * np.sin(omega_d * t)))
        else:
            # Critically damped or overdamped
            response = (force_amplitude/k) * (1 - np.exp(-omega_n * t) * (1 + omega_n * t))
        
        plt.figure(figsize=(10, 6))
        plt.plot(t, response * 1000)  # Convert to mm
        plt.xlabel('Time (s)')
        plt.ylabel('Displacement (mm)')
        plt.title('Step Response')
        plt.grid(True)
        plt.show()

# Example usage
if __name__ == "__main__":
    # Example material properties (Carbon Fiber)
    material = MaterialProperties(
        E_axial=120,  # GPa
        E_transverse=8,  # GPa
        G=4.5,  # GPa
        nu=0.3,
        rho=1600,  # kg/m³
        cost_per_kg=50,  # £/kg
        damping_ratio=0.01
    )
    
    # Example geometry
    geometry = ForkGeometry(
        length=0.4,  # m
        outer_diameter=0.03,  # m
        wall_thickness=0.002  # m
    )
    
    # Create simulation
    fork = ForkSimulation(material, geometry)
    
    # Print basic properties
    print(f"Fork mass: {fork.mass:.2f} kg")
    print(f"Fork cost: £{fork.cost:.2f}")
    print(f"Natural frequency (1st mode): {fork.natural_frequency():.2f} Hz")
    
    # Example analysis
    fork.plot_stress_distribution(axial_force=1000, transverse_force=500)  # 1000N axial, 500N transverse
    fork.plot_frequency_response(force_amplitude=100, frequency_range=(0, 100))  # 100N force, 0-100Hz range
    
    # Time domain analysis
    fork.plot_steady_state_vibration(force_amplitude=100, frequency=10)  # 100N at 10Hz
    fork.plot_step_response(force_amplitude=100)  # 100N step force 