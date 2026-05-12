
import sys
import pkg_resources

def check_versions():
    print(f"Python version: {sys.version}")
    print("\nPackage versions:")
    
    packages = [
        'langchain',
        'langgraph', 
        'langchain_openai',
        'langchain_community',
        'fastapi',
        'uvicorn'
    ]
    
    for package in packages:
        try:
            version = pkg_resources.get_distribution(package).version
            print(f"  {package}: {version}")
        except:
            print(f"  {package}: NOT INSTALLED")

if __name__ == "__main__":
    check_versions()