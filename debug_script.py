import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Util.Parser import ScriptParser
from Util.RunScriptClass import RunScriptCMDClass
from Util.RunScriptClass import StopFlag

script_path = r'd:\KeymouseGo-master\scripts\0228_1419.json5'

print(f"Testing script: {script_path}")
print(f"Script exists: {os.path.exists(script_path)}")

try:
    print("\n=== Parsing script ===")
    head_object = ScriptParser.parse(script_path)
    print(f"Parse result: {head_object}")
    
    if head_object:
        print(f"Head object content: {head_object.content}")
        print(f"Head object type: {head_object.content.get('type')}")
        
        print("\n=== Testing script runner ===")
        flag = StopFlag()
        runner = RunScriptCMDClass([script_path], 1, flag)
        
        print("Running script...")
        runner.run()
        print("Script run completed!")
        
except Exception as e:
    print(f"\nERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
