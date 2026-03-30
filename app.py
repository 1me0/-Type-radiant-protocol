@app.route('/api/intelligence-trend')
def get_trend():
    # Fetch the last 30 scores for the graph
    data = db.execute("SELECT score, timestamp FROM intelligence_trends ORDER BY timestamp DESC LIMIT 30").fetchall()
    return jsonify(data)
    
