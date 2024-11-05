from javsp.config import Cfg 
def prompt(message: str, what: str) -> str:
    if Cfg().other.interactive:
        return input(message)
    else:
        print(f"缺少{what}")
        exit(1)
