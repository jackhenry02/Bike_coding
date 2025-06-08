import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from composite_layup import PlyProperties, CompositeLayup, create_symmetric_layup
from fork_simulation import MaterialProperties, ForkGeometry, ForkSimulation

class ForkSimulationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Composite Fork Simulator")
        self.root.geometry("1200x800")
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.layup_tab = ttk.Frame(self.notebook)
        self.manual_tab = ttk.Frame(self.notebook)
        self.simulation_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.layup_tab, text='Composite Layup')
        self.notebook.add(self.manual_tab, text='Manual Composite Entry')
        self.notebook.add(self.simulation_tab, text='Fork Simulation')
        
        self.setup_layup_tab()
        self.setup_simulation_tab()
        
        # Store current layup and simulation
        self.current_layup = None
        self.current_simulation = None
        
    def setup_layup_tab(self):
        # Left frame for ply properties
        left_frame = ttk.LabelFrame(self.layup_tab, text="Ply Properties")
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        # Ply properties inputs
        properties = [
            ("E11 (GPa):", "e11", 138),
            ("E22 (GPa):", "e22", 9),
            ("nu12:", "nu12", 0.3),
            ("G12 (GPa):", "g12", 6.9),
            ("Thickness (mm):", "thickness", 0.1)
        ]
        
        self.ply_vars = {}
        for i, (label, name, default) in enumerate(properties):
            ttk.Label(left_frame, text=label).grid(row=i, column=0, padx=5, pady=2, sticky='e')
            var = tk.DoubleVar(value=default)
            self.ply_vars[name] = var
            ttk.Entry(left_frame, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=2)
        
        # Orientation inputs
        ttk.Label(left_frame, text="Orientations (degrees):").grid(row=len(properties), column=0, padx=5, pady=5, sticky='e')
        self.orientations_var = tk.StringVar(value="0,45,-45,0")
        ttk.Entry(left_frame, textvariable=self.orientations_var, width=20).grid(row=len(properties), column=1, padx=5, pady=5)
        
        # Create layup button
        ttk.Button(left_frame, text="Create Layup", command=self.create_layup).grid(row=len(properties)+1, column=0, columnspan=2, pady=10)
        
        # Right frame for results
        right_frame = ttk.LabelFrame(self.layup_tab, text="Effective Properties")
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        # Results display
        self.results_text = tk.Text(right_frame, height=10, width=40)
        self.results_text.pack(padx=5, pady=5, fill='both', expand=True)
        
    def setup_simulation_tab(self):
        # Left frame for simulation parameters
        left_frame = ttk.LabelFrame(self.simulation_tab, text="Simulation Parameters")
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        # Fork geometry inputs
        geometry_frame = ttk.LabelFrame(left_frame, text="Fork Geometry")
        geometry_frame.pack(fill='x', padx=5, pady=5)
        
        geometry_params = [
            ("Length (m):", "length", 0.4),
            ("Outer Diameter (m):", "outer_diameter", 0.03),
            ("Wall Thickness (m):", "wall_thickness", 0.002)
        ]
        
        self.geometry_vars = {}
        for i, (label, name, default) in enumerate(geometry_params):
            ttk.Label(geometry_frame, text=label).grid(row=i, column=0, padx=5, pady=2, sticky='e')
            var = tk.DoubleVar(value=default)
            self.geometry_vars[name] = var
            ttk.Entry(geometry_frame, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=2)
        
        # Load inputs
        load_frame = ttk.LabelFrame(left_frame, text="Loads")
        load_frame.pack(fill='x', padx=5, pady=5)
        
        load_params = [
            ("Axial Force (N):", "axial_force", 1000),
            ("Transverse Force (N):", "transverse_force", 500),
            ("Vibration Force (N):", "vibration_force", 100),
            ("Vibration Frequency (Hz):", "vibration_freq", 10)
        ]
        
        self.load_vars = {}
        for i, (label, name, default) in enumerate(load_params):
            ttk.Label(load_frame, text=label).grid(row=i, column=0, padx=5, pady=2, sticky='e')
            var = tk.DoubleVar(value=default)
            self.load_vars[name] = var
            ttk.Entry(load_frame, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=2)
        
        # Analysis buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="Stress Analysis", command=self.run_stress_analysis).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Vibration Analysis", command=self.run_vibration_analysis).pack(side='left', padx=5)
        
        # Right frame for plots
        self.plot_frame = ttk.LabelFrame(self.simulation_tab, text="Results")
        self.plot_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
    def create_layup(self):
        try:
            # Get ply properties
            ply_props = PlyProperties(
                E11=self.ply_vars['e11'].get(),
                E22=self.ply_vars['e22'].get(),
                nu12=self.ply_vars['nu12'].get(),
                G12=self.ply_vars['g12'].get(),
                thickness=self.ply_vars['thickness'].get(),
                orientation=0  # Will be set in layup
            )
            
            # Get orientations
            orientations = [float(x.strip()) for x in self.orientations_var.get().split(',')]
            
            # Create layup
            self.current_layup = create_symmetric_layup(ply_props, orientations)
            effective_props = self.current_layup.calculate_effective_properties()
            
            # Display results
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Effective Laminate Properties:\n")
            self.results_text.insert(tk.END, f"E_x: {effective_props['E_x']:.2f} GPa\n")
            self.results_text.insert(tk.END, f"E_y: {effective_props['E_y']:.2f} GPa\n")
            self.results_text.insert(tk.END, f"nu_xy: {effective_props['nu_xy']:.3f}\n")
            self.results_text.insert(tk.END, f"G_xy: {effective_props['G_xy']:.2f} GPa\n")
            self.results_text.insert(tk.END, f"Total thickness: {effective_props['thickness']:.2f} mm\n")
            
            messagebox.showinfo("Success", "Layup created successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create layup: {str(e)}")
    
    def run_stress_analysis(self):
        if not self.current_layup:
            messagebox.showerror("Error", "Please create a layup first!")
            return
            
        try:
            # Get effective properties
            effective_props = self.current_layup.calculate_effective_properties()
            
            # Create material properties from layup
            material = MaterialProperties(
                E_axial=effective_props['E_x'],
                E_transverse=effective_props['E_y'],
                G=effective_props['G_xy'],
                nu=effective_props['nu_xy'],
                rho=1600,  # Assuming density
                cost_per_kg=50,  # Assuming cost
                damping_ratio=0.01
            )
            
            # Create geometry
            geometry = ForkGeometry(
                length=self.geometry_vars['length'].get(),
                outer_diameter=self.geometry_vars['outer_diameter'].get(),
                wall_thickness=self.geometry_vars['wall_thickness'].get()
            )
            
            # Create simulation
            self.current_simulation = ForkSimulation(material, geometry)
            
            # Run analysis
            axial_force = self.load_vars['axial_force'].get()
            transverse_force = self.load_vars['transverse_force'].get()
            
            # Create figure
            fig = plt.figure(figsize=(8, 6))
            self.current_simulation.plot_stress_distribution(axial_force, transverse_force)
            
            # Clear previous plot
            for widget in self.plot_frame.winfo_children():
                widget.destroy()
            
            # Add new plot
            canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run stress analysis: {str(e)}")
    
    def run_vibration_analysis(self):
        if not self.current_layup:
            messagebox.showerror("Error", "Please create a layup first!")
            return
            
        try:
            # Get effective properties
            effective_props = self.current_layup.calculate_effective_properties()
            
            # Create material properties from layup
            material = MaterialProperties(
                E_axial=effective_props['E_x'],
                E_transverse=effective_props['E_y'],
                G=effective_props['G_xy'],
                nu=effective_props['nu_xy'],
                rho=1600,  # Assuming density
                cost_per_kg=50,  # Assuming cost
                damping_ratio=0.01
            )
            
            # Create geometry
            geometry = ForkGeometry(
                length=self.geometry_vars['length'].get(),
                outer_diameter=self.geometry_vars['outer_diameter'].get(),
                wall_thickness=self.geometry_vars['wall_thickness'].get()
            )
            
            # Create simulation
            self.current_simulation = ForkSimulation(material, geometry)
            
            # Create figure with subplots
            fig = plt.figure(figsize=(12, 8))
            
            # Plot frequency response
            plt.subplot(2, 1, 1)
            self.current_simulation.plot_frequency_response(
                self.load_vars['vibration_force'].get(),
                (0, 100)
            )
            
            # Plot steady state vibration
            plt.subplot(2, 1, 2)
            self.current_simulation.plot_steady_state_vibration(
                self.load_vars['vibration_force'].get(),
                self.load_vars['vibration_freq'].get()
            )
            
            plt.tight_layout()
            
            # Clear previous plot
            for widget in self.plot_frame.winfo_children():
                widget.destroy()
            
            # Add new plot
            canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run vibration analysis: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ForkSimulationGUI(root)
    root.mainloop() 