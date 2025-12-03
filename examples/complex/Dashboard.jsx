import React, { useState, useEffect, useContext } from 'react';
import { ThemeContext } from './ThemeContext';

const Dashboard = ({ user, widgets }) => {
  const theme = useContext(ThemeContext);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/dashboard');
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleWidgetClick = (widgetId) => {
    console.log('Widget clicked:', widgetId);
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className={`dashboard ${theme}`}>
      <header>
        <h1>Welcome, {user.name}</h1>
      </header>
      <main>
        <div className="widgets-grid">
          {widgets.map(widget => (
            <div
              key={widget.id}
              className="widget"
              onClick={() => handleWidgetClick(widget.id)}
            >
              <h3>{widget.title}</h3>
              <p>{widget.content}</p>
            </div>
          ))}
        </div>
      </main>
      {data && (
        <footer>
          <p>Last updated: {data.lastUpdate}</p>
        </footer>
      )}
    </div>
  );
};

export default Dashboard;

