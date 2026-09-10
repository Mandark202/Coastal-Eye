import sys
import os

# Ensure backend module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import inspect
from backend.database import SessionLocal, engine
from backend.models import User, Post, Comment, Alert, AidRequest

# Create a session
db = SessionLocal()

MODELS = {
    "User": User,
    "Post": Post,
    "Comment": Comment,
    "Alert": Alert,
    "AidRequest": AidRequest
}

def get_model_pk(model):
    """Returns the primary key name of the model (usually 'id')."""
    return inspect(model).primary_key[0].name

def get_column_names(model):
    return [c.key for c in inspect(model).attrs if hasattr(c, 'key')]

def list_items(model):
    items = db.query(model).all()
    print(f"\n--- Found {len(items)} {model.__name__}s ---")
    columns = get_column_names(model)
    # limit columns for display to avoid clutter
    display_cols = columns[:6] 
    
    header = " | ".join(display_cols)
    print(header)
    print("-" * len(header))
    
    for item in items:
        values = []
        for col in display_cols:
            val = getattr(item, col)
            values.append(str(val))
        print(" | ".join(values))

def delete_item(model):
    pk_name = get_model_pk(model)
    item_id = input(f"Enter {pk_name} to delete: ")
    
    pk_column = getattr(model, pk_name)
    try:
        if pk_column.type.python_type == int:
             item_id = int(item_id)
    except:
        pass 

    item = db.query(model).filter(getattr(model, pk_name) == item_id).first()
    if item:
        db.delete(item)
        db.commit()
        print(f"Item {item_id} deleted.")
    else:
        print("Item not found.")

def edit_item(model):
    pk_name = get_model_pk(model)
    item_id = input(f"Enter {pk_name} to edit: ")
    
    pk_column = getattr(model, pk_name)
    try:
        if pk_column.type.python_type == int:
             item_id = int(item_id)
    except:
        pass 

    item = db.query(model).filter(getattr(model, pk_name) == item_id).first()
    if not item:
        print("Item not found.")
        return

    print("\nCurrent Values:")
    cols = get_column_names(model)
    for col in cols:
        print(f"{col}: {getattr(item, col)}")
    
    print("\nEnter updates in format 'field=value'. Leave empty to stop.")
    while True:
        update_str = input("Update (field=value): ")
        if not update_str.strip():
            break
        
        if '=' not in update_str:
            print("Invalid format. Use field=value")
            continue
            
        field, value = update_str.split('=', 1)
        field = field.strip()
        value = value.strip()
        
        if not hasattr(item, field):
            print(f"Model {model.__name__} has no field '{field}'")
            continue
            
        # Try to guess type
        current_val = getattr(item, field)
        try:
            target_type = type(current_val)
            
            if target_type == bool:
                if value.lower() in ['true', '1']: new_val = True
                elif value.lower() in ['false', '0']: new_val = False
                else: new_val = bool(value)
            elif target_type == int:
                new_val = int(value)
            elif target_type == float:
                new_val = float(value)
            elif current_val is None:
                new_val = value
            else:
                new_val = value
            
            setattr(item, field, new_val)
            print(f"Set {field} to {new_val}")
        except Exception as e:
            print(f"Error setting value: {e}")
            
    db.commit()
    print("Updates saved.")

def create_admin_user():
    # Helper to quickly add a test user if needed
    from backend.routers.auth import get_password_hash
    existing = db.query(User).filter(User.email == "admin@coastal.com").first()
    if not existing:
        # Check if we need to provide a password or hashed_password
        # In the original file it was hashed_password
        u = User(name="Admin", email="admin@coastal.com", hashed_password=get_password_hash("admin123"), role="authority")
        db.add(u)
        db.commit()
        print("Created admin user (admin@coastal.com / admin123)")
    else:
        print("Admin user already exists.")

def manage_model(model_name):
    model = MODELS[model_name]
    while True:
        print(f"\n--- Managing {model_name} ---")
        print("1. List")
        print("2. Delete")
        print("3. Edit")
        if model_name == "User":
            print("5. Create Test Admin User")
        print("4. Back")
        
        c = input("Choice: ")
        if c == '1':
            list_items(model)
        elif c == '2':
            delete_item(model)
        elif c == '3':
            edit_item(model)
        elif c == '4':
            break
        elif c == '5' and model_name == "User":
            create_admin_user()

def main_menu():
    while True:
        print("\n=== Database Manager ===")
        model_names = list(MODELS.keys())
        for i, m in enumerate(model_names):
            print(f"{i+1}. {m}")
        print("Q. Quit")
        
        choice = input("Select table: ")
        if choice.lower() == 'q':
            break
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(model_names):
                manage_model(model_names[idx])
            else:
                print("Invalid selection")
        except ValueError:
            print("Invalid input")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()
