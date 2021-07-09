import argparse
import os
import sys
import glob
import shutil
import subprocess
import getpass
import pathlib
import pdb

class CColors:
    DIR ='\033[95m'
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# A colored arrow for printing
colored_arrow = CColors.OKCYAN + " --> " + CColors.DIR

def check_version():
    # Check python version number
    python_version = sys.version_info
    ver_num = str(python_version.major) + "." + str(python_version.minor)

    if python_version.major < 3:
        print(CColors.FAIL + "Error: python version is " + ver_num + ", but 3.6 or greater is required.")
        
        python_executable = sys.executable
        print("Hint: the current python executable is " + CColors.DIR + python_executable + CColors.FAIL + ". Is that the same path you get when you run `which python`? Did you run this script with `sudo python`? Doing so can affect which python executable gets launched, and sudo python can be different from non-sudo python.")
        print("Hint: try running with python3 instead of python." + CColors.ENDC)
        sys.exit()

def main():

    # Default profile 
    default_profile = os.path.join(str(pathlib.Path.home()), '.bash_profile')
    
    # Check the python version
    check_version()

    parser = argparse.ArgumentParser(description="Install a self-signed SSL certificate")
    parser.add_argument('--cert', type=str, default=None, help="Path to the SSL certificate")
    parser.add_argument('--custom-name', type=str, default=None, help = "Name under which to install the certificate (default: same as cert file name)")
    parser.add_argument('--ca-certificates-dir', type=str, default = "/usr/local/share/ca-certificates", help = "Directory in which to install the certificate (default: /usr/share/ca-certificates)")
    parser.add_argument('--profile', type=str, default=default_profile, help = "Shell profile (default: " + default_profile + ")")
    parser.add_argument('--install-cert', action = "store_true", help = "Install certificate to ca-certificates")
    parser.add_argument('--setup-python', action = "store_true", help = "Setup environmental variables for python applications (e.g., pip, conda)")
    args = parser.parse_args()
    cert = args.cert
    custom_name = args.custom_name
    ca_certificates_dir = args.ca_certificates_dir
    profile = args.profile
    setup_python = args.setup_python
    install_cert = args.install_cert

    if install_cert is False and setup_python is False:
        print("No actions specified. Call " + os.path.basename(__file__) + " with one or both of --install-cert, --setup-python")
        return

    if install_cert is True:
        # If no certificate was supplied, search for one
        if cert is None:
            valid_extensions = ["*.cer", "*.crt", "*.cert"]
            matching_files = []
            for ext in valid_extensions:
                files = glob.glob(ext)
                for file in files:
                    matching_files.append(os.path.abspath(os.path.expanduser(file)))
            if len(matching_files) == 0:
                print(CColors.FAIL + "Error: no certificate supplied and no certificate files found in current directory. Exiting." + CColors.ENDC)
                return
            else:
                for file in matching_files:
                    use_this_one = input("Use " + CColors.DIR + file + CColors.ENDC + " [y/N]? " + CColors.ENDC)
                    if use_this_one.lower() == "y":
                        cert = file
                        break
        else:
            cert = os.path.abspath(os.path.expanduser(cert))
            if not os.path.isfile(cert):
                print(CColors.FAIL + "Error: " + CColors.DIR + cert  + CColors.FAIL + " not found." + CColors.ENDC)
                return

        # Still no certs found
        if cert is None:
            print("No certificates found")
            return
        
        # Cert was found:
        cert = os.path.abspath(os.path.expanduser(cert))
        print("Found " + CColors.DIR + cert + CColors.ENDC)
        filename, ext = os.path.splitext(cert)
        if ext != ".crt":

            # Get the extension
            cert_dir,_  = os.path.split(cert)
            old_file_path = cert
            
            # Make new file name with .crt extension
            new_file_path = os.path.join(cert_dir, filename + ".crt")
            print("Copying " + CColors.DIR + old_file_path + CColors.ENDC +  " --> " + CColors.DIR + new_file_path + CColors.ENDC)

            # Copy the certificate to one with a .crt extension
            subprocess.Popen("cp " + old_file_path + " " + new_file_path, shell=True).wait()

            # Work with the new filepath from now on
            cert = new_file_path
        
        # Rename the certificate to the custom name if one was supplied
        if custom_name is None:
            _, dst_filename = os.path.split(cert)
        else:
            dst_filename = custom_name.replace(".crt", "") + ".crt"  
        
        # Where to put the certificate
        dst_filepath = os.path.join(ca_certificates_dir, dst_filename)

        # Make the certificate directory
        if not os.path.isdir(ca_certificates_dir):
            print("Creating " + CColors.DIR + ca_certificates_dir + CColors.ENDC)
            subprocess.Popen("sudo mkdir -p " + ca_certificates_dir, shell=True).wait()

        # Move the certificate file
        print("Moving " + CColors.DIR + cert + CColors.ENDC +  " --> " + CColors.DIR + dst_filepath + CColors.ENDC)
        subprocess.Popen("sudo mv " + cert + " " + dst_filepath, shell=True).wait()
        
        # Check that it worked
        if not os.path.isfile(dst_filepath):
            print(CColors.FAIL + "Error copying " + CColors.DIR + cert + CColors.FAIL + " --> " + CColors.DIR + dst_filepath + CColors.ENDC)
            exit

        # Command to run sudo update-ca-certificates
        subprocess.Popen("sudo update-ca-certificates", shell=True).wait()

        # See if the .pem file made it into /etc/ssl/certs
        pem_file_name = dst_filename.replace(".crt", ".pem")
        pem_file_path = os.path.join("/etc/ssl/certs", pem_file_name)
        if os.path.isfile(pem_file_path):
            print(CColors.OKCYAN + "Copied " + CColors.DIR + cert + CColors.OKCYAN + " --> " + CColors.DIR + pem_file_path + CColors.ENDC)
        else:
            print(CColors.FAIL + "Error copying " + CColors.DIR + cert + CColors.FAIL + " --> " + CColors.DIR + pem_file_path + CColors.ENDC)
            return

    # Set up environmental variables    
    # Check if each one is an environmental variable
    if setup_python is True:
        env_vars = ["PIP_CERT", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"]
        for var in env_vars:
            if os.getenv(var) is None:

                # Create the profile file if it doesn't already exist    
                if not os.path.isfile(profile):
                    pathlib.Path(profile).touch()

                # Open the file and search for the variable. 
                # This accounts for the variable having already been added
                # to the file but not yet set in the shell that launched proxy.py
                var_in_file = False
                with open(profile, 'r') as f:
                    for line in f:
                        if var in line:
                            if line.lstrip()[0] != "#": # Make sure the line isn't commented out
                                print("Found " + CColors.DIR + line.replace("\n", '') + CColors.ENDC + " in " + CColors.DIR + profile + CColors.ENDC)
                                var_in_file=True
                                break
                if var_in_file is False:
                    with open(profile, 'a') as f:
                        cmd = "export " + var + "=/etc/ssl/certs/ca-certificates.crt"
                        print("Appending " + CColors.DIR + cmd + CColors.ENDC + " to " + CColors.DIR + profile + CColors.ENDC)
                        f.write(cmd + "\n")
            else:
                print(CColors.OKCYAN + "Environmental variable already set: " + CColors.DIR + var + "=" + os.getenv(var) + CColors.ENDC)
        unset_vars = [var for var in env_vars if os.getenv(var) is None]
        if len(unset_vars) > 0:
            print("The following required environmental variables are unset in the current shell: " + CColors.DIR + str(unset_vars) + CColors.ENDC)
            print("Log out and then log back in to update environmental variables.")
    
if __name__ == "__main__":
    main()
