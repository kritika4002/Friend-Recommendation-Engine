# Friend Recommendation Engine

A modern web application that provides friend recommendations using Neo4j graph database and Flask. The system analyzes user connections to suggest potential friends based on mutual connections and influence scores.

## Features

- User Management
  - Add new users to the system
  - View list of all users
- Friendship Management
  - Create friendship connections between users
- Smart Recommendations
  - Get personalized friend recommendations based on:
    - Number of mutual friends
    - User influence (PageRank score)
    - Community detection
- Modern Web Interface
  - Clean and responsive design
  - Intuitive user interactions
  - Real-time updates

## Technical Stack

- **Backend**: Python Flask
- **Database**: Neo4j Graph Database
- **Frontend**: HTML, CSS
- **Graph Algorithms**: 
  - PageRank (for influence scoring)
  - Community Detection (WCC/Union-Find)

## Setup Requirements

1. Python with Flask installed
2. Neo4j Database Server
3. Python Neo4j Driver

## Configuration

1. Install required Python packages:
   ```bash
   pip install flask neo4j
   ```

2. Configure Neo4j connection in `app.py`:
   ```python
   URI = "neo4j://localhost:7687"
   AUTH = ("neo4j", "your_password")  # Update with your Neo4j password
   ```

3. Set up your Flask secret key in `app.py`:
   ```python
   app.secret_key = 'your_super_secret_key'
   ```

## Running the Application

1. Start your Neo4j database server
2. Run the Flask application:
   ```bash
   python app.py
   ```
3. Access the application at `http://localhost:5000`

## Features in Detail

### User Management
- Add new users to the system
- View complete list of users
- Each user has a unique identifier

### Friend Recommendations
- Algorithm considers:
  - Number of mutual friends
  - User's influence score (PageRank)
  - Community membership
- Top 10 recommendations displayed per user

### Community Detection
- Users are grouped into communities
- Community ID displayed for each user
- Helps in understanding user clusters

## Contributing

Feel free to contribute to this project by submitting issues or pull requests.

## License

This project is open source and available under the MIT License.