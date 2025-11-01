from flask import Flask, render_template, request, redirect, url_for, flash
from neo4j import GraphDatabase
import atexit

app = Flask(__name__)
# A secret key is required to use 'flash' messages
app.secret_key = 'your_super_secret_key' 

# --- 1. Neo4j Connection ---
# IMPORTANT: Change this to your own password
URI = "neo4j://localhost:7687"
AUTH = ("neo4j", "12345678") # <-- UPDATE THIS

try:
    driver = GraphDatabase.driver(URI, auth=AUTH)
    driver.verify_connectivity()
    print("Neo4j connection successful.")
except Exception as e:
    print(f"Failed to connect to Neo4j. Is it running? Error: {e}")
    exit()

# --- 2. Database Functions (Read) ---
def get_user_list():
    """Fetches all user names from the database."""
    with driver.session() as session:
        result = session.run("MATCH (u:User) RETURN u.name AS name ORDER BY name")
        return [record["name"] for record in result]

def get_recommendations(user_name):
    """Runs the recommendation query for the selected user."""
    query = """
    MATCH (u1:User {name: $userName})
          -[:FRIENDS_WITH]->(friend:User)
          -[:FRIENDS_WITH]->(fof:User)
    WHERE u1 <> fof AND NOT (u1)-[:FRIENDS_WITH]->(fof)
    RETURN fof.name AS Recommendation, 
           fof.pageRankScore AS Influence, 
           count(DISTINCT friend) AS MutualFriends
    ORDER BY MutualFriends DESC, Influence DESC
    LIMIT 10
    """
    with driver.session() as session:
        result = session.run(query, userName=user_name)
        return [record.data() for record in result]

def get_community(user_name):
    """Finds the user's community ID (from WCC/Union-Find)."""
    query = "MATCH (u:User {name: $userName}) RETURN u.communityId AS community"
    with driver.session() as session:
        result = session.run(query, userName=user_name).single()
        return result["community"] if result else "N/A"

# --- 3. Flask Routes (CRUD Operations) ---

@app.route('/', methods=['GET', 'POST'])
def index():
    users = get_user_list()
    selected_user = None
    recommendations = []
    community_id = None
    
    if request.method == 'POST':
        # This is for the recommendation form
        selected_user = request.form.get('user')
        if selected_user:
            recommendations = get_recommendations(selected_user)
            community_id = get_community(selected_user)
            
    return render_template('index.html', 
                           users=users, 
                           selected_user=selected_user,
                           recommendations=recommendations, 
                           community_id=community_id)

# --- CREATE ---
@app.route('/add_user', methods=['POST'])
def add_user():
    user_name = request.form.get('user_name')
    if user_name:
        with driver.session() as session:
            # Create a user with a unique name
            session.run("CREATE (u:User {name: $name, userId: $userId})", 
                        name=user_name, userId=user_name.lower())
            flash(f"User '{user_name}' created. Run GDS Algorithms to update scores.", "warning")
    else:
        flash("User name cannot be empty.", "error")
    # Redirect back to the main page
    return redirect(url_for('index'))

# --- CREATE (Relationship) ---
@app.route('/add_friendship', methods=['POST'])
def add_friendship():
    user1 = request.form.get('user1')
    user2 = request.form.get('user2')
    if user1 and user2 and user1 != user2:
        with driver.session() as session:
            session.run("""
                MATCH (a:User {name: $user1})
                MATCH (b:User {name: $user2})
                MERGE (a)-[:FRIENDS_WITH]->(b)
            """, user1=user1, user2=user2)
            flash(f"Friendship added. Run GDS Algorithms to update scores.", "warning")
    else:
        flash("Please select two different users.", "error")
    return redirect(url_for('index'))

# --- UPDATE ---
@app.route('/update_user', methods=['POST'])
def update_user():
    old_name = request.form.get('old_name')
    new_name = request.form.get('new_name')
    if old_name and new_name:
        with driver.session() as session:
            session.run("MATCH (u:User {name: $old}) SET u.name = $new, u.userId = $newId", 
                        old=old_name, new=new_name, newId=new_name.lower())
            flash(f"User '{old_name}' updated to '{new_name}'!", "success")
    else:
        flash("Both names are required for update.", "error")
    return redirect(url_for('index'))

# --- DELETE ---
@app.route('/delete_user', methods=['POST'])
def delete_user():
    user_name = request.form.get('user_name')
    if user_name:
        with driver.session() as session:
            # DETACH DELETE removes the node AND any relationships connected to it
            session.run("MATCH (u:User {name: $name}) DETACH DELETE u", name=user_name)
            flash(f"User '{user_name}' and all their friendships deleted!", "success")
            flash("Run GDS Algorithms to update scores.", "warning")
    else:
        flash("Please select a user to delete.", "error")
    return redirect(url_for('index'))

# --- DELETE (Relationship) ---
@app.route('/delete_friendship', methods=['POST'])
def delete_friendship():
    user1 = request.form.get('user1')
    user2 = request.form.get('user2')
    if user1 and user2 and user1 != user2:
        with driver.session() as session:
            # This query is direction-agnostic
            # It finds the friendship regardless of who initiated it
            session.run("""
                MATCH (a:User {name: $user1})-[r:FRIENDS_WITH]-(b:User {name: $user2})
                DELETE r
            """, user1=user1, user2=user2)
            flash(f"Friendship between '{user1}' and '{user2}' deleted.", "success")
            flash("Run GDS Algorithms to update scores.", "warning")
    else:
        flash("Please select two different users.", "error")
    return redirect(url_for('index'))


# --- 4. GDS Algorithm Runner ---
def run_gds_algorithms():
    """Runs all GDS algorithms to refresh scores."""
    with driver.session() as session:
        # 1. Drop the old graph (if it exists) so we can recreate it
        session.run("CALL gds.graph.drop('socialGraph', false)")
        
        # 2. Project the new graph with the latest data
        session.run("""
            CALL gds.graph.project(
              'socialGraph',
              'User',
              'FRIENDS_WITH'
            )
        """)
        
        # 3. Run PageRank
        session.run("""
            CALL gds.pageRank.write('socialGraph', {
              writeProperty: 'pageRankScore'
            })
        """)
        
        # 4. Run WCC
        session.run("""
            CALL gds.wcc.write('socialGraph', {
              writeProperty: 'communityId'
            })
        """)

# This is the new route that the button will call
@app.route('/run_gds', methods=['POST'])
def run_gds_route():
    try:
        run_gds_algorithms()
        flash("Successfully updated all PageRank and Community scores!", "success")
    except Exception as e:
        flash(f"An error occurred: {e}", "error")
    return redirect(url_for('index'))


# --- 5. Cleanup & Run ---
def close_driver():
    """Closes the Neo4j driver connection when the app shuts down."""
    if driver:
        driver.close()
        print("Neo4j connection closed.")

atexit.register(close_driver) # Make sure driver closes when app stops

if __name__ == '__main__':
    app.run(debug=True)