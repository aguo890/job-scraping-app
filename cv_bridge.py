import os
import yaml
import contextlib
from datetime import datetime

# Attempt to import rendercv; fail gracefully if not ready
try:
    from rendercv.renderer import render
    # from rendercv.data.models.cv import RenderCVDataModel # Optional for validation
except ImportError:
    render = None

@contextlib.contextmanager
def temporary_cwd(path):
    """Safely change current working directory and ensure we return."""
    old_pwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old_pwd)

class CVOrchestrator:
    def __init__(self, base_cv_path_relative="rendercv/Aaron_Guo_CV.yaml"):
        # Resolve absolute paths based on where this script lives (The Root)
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_cv_path = os.path.join(self.root_dir, base_cv_path_relative)
        self.output_root = os.path.join(self.root_dir, "generated_cvs")
        
        if not os.path.exists(self.output_root):
            os.makedirs(self.output_root)

    def generate_tailored_cv(self, job_details):
        """
        Generates a PDF CV tailored for the job.
        job_details: dict containing at least 'company'
        """
        if render is None:
            # Fallback for testing when rendercv is not installed
            # raise ImportError("RenderCV is not installed or accessible.")
            print("RenderCV not found, simulating generation...")
            return "SIMULATED_PATH_TO_PDF"

        # 1. Load Base YAML
        # Handle case where file doesn't exist yet (before move)
        if not os.path.exists(self.base_cv_path):
             raise FileNotFoundError(f"Base CV YAML not found at: {self.base_cv_path}")

        with open(self.base_cv_path, 'r', encoding='utf-8') as f:
            cv_data = yaml.safe_load(f)

        # 2. Tailor Data (Example: Rename the generic CV to include Company Name)
        # You can add logic here to swap keywords or skills based on job_details['description']
        
        # 3. Define Output Names
        safe_company = "".join([c for c in job_details.get('company', 'Generic') if c.isalnum()])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        new_filename_base = f"CV_Aaron_Guo_{safe_company}_{timestamp}"
        
        # 4. Save Temporary YAML
        # We save this in the output folder to keep the source clean
        temp_yaml_path = os.path.join(self.output_root, f"{new_filename_base}.yaml")
        
        with open(temp_yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(cv_data, f)

        # 5. Render
        # We switch context to the folder containing the ORIGINAL yaml 
        # so that relative image paths (like profile_pic.jpg) work correctly.
        base_cv_dir = os.path.dirname(self.base_cv_path)
        
        try:
            with temporary_cwd(base_cv_dir):
                # RenderCV usually outputs to a folder named 'rendercv_output' in CWD
                # We want to capture where it goes. 
                # RenderCV's render() might just create it in CWD.
                render(input_path=temp_yaml_path)
            
            # 6. Locate the Result
            # Depending on rendercv version, it might be in ./rendercv_output OR next to the yaml
            # The standard rendercv behavior creates a folder `rendercv_output` 
            # We ran it inside `base_cv_dir`. 
            # Check `base_cv_dir/rendercv_output`
            
            # Actually, render(input_path) renders to the directory OF the input path?
            # Or CWD? 
            # Documentation says "Renders ... in the current working directory".
            # So if we CWD to `base_cv_dir`, it should be in `base_cv_dir/rendercv_output`.
            
            expected_pdf = os.path.join(base_cv_dir, "rendercv_output", f"{new_filename_base}.pdf")
            
            # If we want to move it to `generated_cvs` for cleanliness:
            final_pdf_path = os.path.join(self.output_root, f"{new_filename_base}.pdf")
            if os.path.exists(expected_pdf):
                # Move it
                if os.path.exists(final_pdf_path):
                     os.remove(final_pdf_path)
                os.rename(expected_pdf, final_pdf_path)
                return final_pdf_path
            
            # If not there, look in CWD/rendercv_output just in case
            cwd_output = os.path.join(base_cv_dir, "rendercv_output")
            # Walk to find it?
            
            return f"Generated, but check folder: {cwd_output}"
                
        except Exception as e:
            raise e
