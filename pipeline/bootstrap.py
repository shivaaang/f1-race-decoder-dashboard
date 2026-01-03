from pipeline.db import bootstrap_warehouse

if __name__ == "__main__":
    bootstrap_warehouse()
    print("Warehouse schemas initialized.")
