import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from composite_layup import PlyProperties, CompositeLayup, create_symmetric_layup
from fork_simulation import MaterialProperties, ForkGeometry, ForkSimulation
import json
import os

class PlyPropertiesFrame(ttk.LabelFrame):
    def __init__(self, parent, ply_number, *args, **kwargs):
        super().__init__(parent, text=f"Ply {ply_number}", *args, **kwargs)
        self.ply_number = ply_number
        
        # Ply properties inputs
        properties = [
            ("E11 (GPa):", "e11", 138),
            ("E22 (GPa):", "e22", 9),
            ("nu12:", "nu12", 0.3),
            ("G12 (GPa):", "g12", 6.9),
            ("Thickness (mm):", "thickness", 0.1),
            ("Orientation (deg):", "orientation", 0)
        ]
        
        self.vars = {}
        for i, (label, name, default) in enumerate(properties):
            ttk.Label(self, text=label).grid(row=i, column=0, padx=5, pady=2, sticky='e')
            var = tk.DoubleVar(value=default)
            self.vars[name] = var
            ttk.Entry(self, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=2)
    
    def get_properties(self) -> PlyProperties:
        return PlyProperties(
            E11=self.vars['e11'].get(),
            E22=self.vars['e22'].get(),
            nu12=self.vars['nu12'].get(),
            G12=self.vars['g12'].get(),
            thickness=self.vars['thickness'].get(),
            orientation=self.vars['orientation'].get()
        )

class MaterialPropertiesFrame(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, text="Material Properties", *args, **kwargs)
        
        # Material properties inputs
        properties = [
            ("Name:", "name", ""),
            ("E_axial (GPa):", "e_axial", 120),
            ("E_transverse (GPa):", "e_transverse", 8),
            ("G (GPa):", "g", 4.5),
            ("nu:", "nu", 0.3),
            ("Density (kg/m³):", "rho", 1600),
            ("Cost per kg (£):", "cost", 50),
            ("Damping ratio:", "damping", 0.01)
        ]
        
        self.vars = {}
        for i, (label, name, default) in enumerate(properties):
            ttk.Label(self, text=label).grid(row=i, column=0, padx=5, pady=2, sticky='e')
            if name == "name":
                var = tk.StringVar(value=default)
            else:
                var = tk.DoubleVar(value=default)
            self.vars[name] = var
            ttk.Entry(self, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=2)
        
        # Description field
        ttk.Label(self, text="Description:").grid(row=len(properties), column=0, padx=5, pady=2, sticky='e')
        self.description_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.description_var, width=30).grid(
            row=len(properties), column=1, padx=5, pady=2)
    
    def get_properties(self) -> dict:
        return {name: var.get() for name, var in self.vars.items()}
    
    def set_properties(self, properties: dict):
        for name, value in properties.items():
            if name in self.vars:
                self.vars[name].set(value)

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
        self.simulation_tab = ttk.Frame(self.notebook)
        self.materials_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.layup_tab, text='Composite Layup')
        self.notebook.add(self.simulation_tab, text='Fork Simulation')
        self.notebook.add(self.materials_tab, text='Material Properties')
        
        self.setup_layup_tab()
        self.setup_simulation_tab()
        self.setup_materials_tab()
        
        # Store current layup and simulation
        self.current_layup = None
        self.current_simulation = None
        self.ply_frames = []
        self.material_properties = {}
        self.load_material_properties()
        
    def setup_layup_tab(self):
        # Top frame for layup configuration
        top_frame = ttk.Frame(self.layup_tab)
        top_frame.pack(fill='x', padx=5, pady=5)
        
        # Number of plies input
        ttk.Label(top_frame, text="Number of Plies:").pack(side='left', padx=5)
        self.num_plies_var = tk.IntVar(value=4)
        num_plies_entry = ttk.Entry(top_frame, textvariable=self.num_plies_var, width=5)
        num_plies_entry.pack(side='left', padx=5)
        
        # Layup type selection
        ttk.Label(top_frame, text="Layup Type:").pack(side='left', padx=5)
        self.layup_type_var = tk.StringVar(value="symmetric")
        ttk.Radiobutton(top_frame, text="Symmetric", variable=self.layup_type_var, 
                       value="symmetric", command=self.update_ply_frames).pack(side='left', padx=5)
        ttk.Radiobutton(top_frame, text="Asymmetric", variable=self.layup_type_var,
                       value="asymmetric", command=self.update_ply_frames).pack(side='left', padx=5)
        
        # Update button
        ttk.Button(top_frame, text="Update Ply Configuration", 
                  command=self.update_ply_frames).pack(side='left', padx=20)
        
        # Create layup button
        ttk.Button(top_frame, text="Create Layup", 
                  command=self.create_layup).pack(side='right', padx=20)
        
        # Main content frame
        content_frame = ttk.Frame(self.layup_tab)
        content_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left frame for ply properties
        self.left_frame = ttk.Frame(content_frame)
        self.left_frame.pack(side='left', fill='both', expand=True)
        
        # Right frame for results
        right_frame = ttk.LabelFrame(content_frame, text="Effective Properties")
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        # Results display
        self.results_text = tk.Text(right_frame, height=10, width=40)
        self.results_text.pack(padx=5, pady=5, fill='both', expand=True)
        
        # Initialize ply frames
        self.update_ply_frames()
        
    def update_ply_frames(self):
        # Clear existing ply frames
        for frame in self.ply_frames:
            frame.destroy()
        self.ply_frames.clear()
        
        # Get number of plies
        num_plies = self.num_plies_var.get()
        is_symmetric = self.layup_type_var.get() == "symmetric"
        
        # Calculate actual number of frames needed
        if is_symmetric:
            num_frames = (num_plies + 1) // 2
        else:
            num_frames = num_plies
        
        # Create new ply frames
        for i in range(num_frames):
            frame = PlyPropertiesFrame(self.left_frame, i + 1)
            frame.grid(row=i, column=0, padx=5, pady=5, sticky='nsew')
            self.ply_frames.append(frame)
            
            if is_symmetric and i == num_frames - 1 and num_plies % 2 == 0:
                # Add a note for middle ply in symmetric layup
                ttk.Label(self.left_frame, 
                         text="(Middle ply - will be duplicated)").grid(
                             row=i, column=1, padx=5, pady=5, sticky='w')
    
    def create_layup(self):
        try:
            # Get ply properties
            plies = []
            for frame in self.ply_frames:
                plies.append(frame.get_properties())
            
            # Create layup based on type
            if self.layup_type_var.get() == "symmetric":
                # For symmetric layup, mirror the plies
                num_plies = self.num_plies_var.get()
                if num_plies % 2 == 0:
                    # Even number of plies
                    plies = plies + plies[::-1]
                else:
                    # Odd number of plies
                    plies = plies[:-1] + plies[::-1]
            
            # Create layup
            self.current_layup = CompositeLayup(plies)
            effective_props = self.current_layup.calculate_effective_properties()
            
            # Display results
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Effective Laminate Properties:\n")
            self.results_text.insert(tk.END, f"E_x: {effective_props['E_x']:.2f} GPa\n")
            self.results_text.insert(tk.END, f"E_y: {effective_props['E_y']:.2f} GPa\n")
            self.results_text.insert(tk.END, f"nu_xy: {effective_props['nu_xy']:.3f}\n")
            self.results_text.insert(tk.END, f"G_xy: {effective_props['G_xy']:.2f} GPa\n")
            self.results_text.insert(tk.END, f"Total thickness: {effective_props['thickness']:.2f} mm\n")
            
            # Add layup sequence
            self.results_text.insert(tk.END, f"\nLayup Sequence:\n")
            for i, ply in enumerate(plies):
                self.results_text.insert(tk.END, 
                    f"Ply {i+1}: {ply.orientation}° (E11={ply.E11/1e9:.1f} GPa, t={ply.thickness*1000:.2f} mm)\n")
            
            messagebox.showinfo("Success", "Layup created successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create layup: {str(e)}")
    
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

    def setup_materials_tab(self):
        # Left frame for material input
        left_frame = ttk.Frame(self.materials_tab)
        left_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        # Material properties input
        self.material_frame = MaterialPropertiesFrame(left_frame)
        self.material_frame.pack(fill='x', padx=5, pady=5)
        
        # Buttons frame
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text="Save Material", 
                  command=self.save_material).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Delete Material", 
                  command=self.delete_material).pack(side='left', padx=5)
        
        # Right frame for material list
        right_frame = ttk.LabelFrame(self.materials_tab, text="Saved Materials")
        right_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        # Material list
        self.material_listbox = tk.Listbox(right_frame, height=10)
        self.material_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        self.material_listbox.bind('<<ListboxSelect>>', self.on_material_select)
        
        # Description display
        self.description_text = tk.Text(right_frame, height=5, width=40)
        self.description_text.pack(fill='x', padx=5, pady=5)
        
        # Update material list
        self.update_material_list()
    
    def save_material(self):
        properties = self.material_frame.get_properties()
        name = properties['name']
        
        if not name:
            messagebox.showerror("Error", "Please enter a material name")
            return
        
        # Add description to properties
        properties['description'] = self.material_frame.description_var.get()
        
        # Save to dictionary
        self.material_properties[name] = properties
        
        # Save to file
        self.save_material_properties()
        
        # Update list
        self.update_material_list()
        messagebox.showinfo("Success", f"Material '{name}' saved successfully")
    
    def delete_material(self):
        selection = self.material_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a material to delete")
            return
        
        name = self.material_listbox.get(selection[0])
        if messagebox.askyesno("Confirm", f"Delete material '{name}'?"):
            del self.material_properties[name]
            self.save_material_properties()
            self.update_material_list()
            self.material_frame.set_properties({})
            self.material_frame.description_var.set("")
    
    def on_material_select(self, event):
        selection = self.material_listbox.curselection()
        if not selection:
            return
        
        name = self.material_listbox.get(selection[0])
        properties = self.material_properties[name]
        
        # Update material frame
        self.material_frame.set_properties(properties)
        self.material_frame.description_var.set(properties.get('description', ''))
        
        # Update description text
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(tk.END, properties.get('description', ''))
    
    def update_material_list(self):
        self.material_listbox.delete(0, tk.END)
        for name in sorted(self.material_properties.keys()):
            self.material_listbox.insert(tk.END, name)
    
    def save_material_properties(self):
        try:
            with open('material_properties.json', 'w') as f:
                json.dump(self.material_properties, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save material properties: {str(e)}")
    
    def load_material_properties(self):
        try:
            if os.path.exists('material_properties.json'):
                with open('material_properties.json', 'r') as f:
                    self.material_properties = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load material properties: {str(e)}")
            self.material_properties = {}

if __name__ == "__main__":
    root = tk.Tk()
    app = ForkSimulationGUI(root)
    root.mainloop() 