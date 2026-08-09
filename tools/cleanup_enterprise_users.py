#!/usr/bin/env python3
"""
Cleanup script to remove enterprise seed users

Removes all users with @enterprise.indoc.local email domain
and their associated data (documents, audit logs, etc.)
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def cleanup_enterprise_users():
    """Remove enterprise seed users and their data"""
    
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='indoc',
        user='postgres',
        password=''
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    try:
        # Get count of users to be deleted
        cur.execute("""
            SELECT COUNT(*) FROM users 
            WHERE email LIKE '%@enterprise.indoc.local'
        """)
        count = cur.fetchone()[0]
        
        if count == 0:
            print("✅ No enterprise users found to delete")
            return
        
        print(f"🗑️  Found {count} enterprise users to delete...")
        
        # Delete users (CASCADE will handle related records)
        cur.execute("""
            DELETE FROM users 
            WHERE email LIKE '%@enterprise.indoc.local'
            RETURNING id, email
        """)
        
        deleted_users = cur.fetchall()
        
        print(f"✅ Deleted {len(deleted_users)} enterprise users:")
        for user_id, email in deleted_users[:10]:  # Show first 10
            print(f"   - {email} (ID: {user_id})")
        
        if len(deleted_users) > 10:
            print(f"   ... and {len(deleted_users) - 10} more")
        
        # Get remaining user count
        cur.execute("SELECT COUNT(*) FROM users")
        remaining = cur.fetchone()[0]
        print(f"\n📊 Remaining users: {remaining}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("ENTERPRISE USER CLEANUP")
    print("=" * 60)
    print("\nThis will delete all users with @enterprise.indoc.local")
    print("and their associated documents, permissions, and audit logs.")
    print("\n⚠️  This action cannot be undone!")
    print("=" * 60)
    
    response = input("\nProceed with cleanup? (yes/no): ").strip().lower()
    
    if response == 'yes':
        cleanup_enterprise_users()
        print("\n✅ Cleanup complete!")
    else:
        print("\n❌ Cleanup cancelled")


