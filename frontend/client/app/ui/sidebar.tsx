import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import RecommendationCard from './recommendation-card';
import connectWithStrava from '/strava/connect-with-strava.svg';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

type SidebarProps = {
  isOpen: boolean;
  toggleSidebar: () => void;
};

const Sidebar: React.FC<SidebarProps> = ({ isOpen, toggleSidebar }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [recommendationData, setRecommendationData] = useState([]);
  const router = useRouter();
  const hasFetchedToken = useRef(false);

  useEffect(() => {
    if (hasFetchedToken.current) {
      return;
    }

    console.log("Sidebar useEffect triggered");
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');

    if (code) {
      console.log("Code found: ", code);
      hasFetchedToken.current = true; // Set the ref to true to indicate the API call is in progress or has been made
      axios.get(`/api/auth?code=${code}`)
        .then(response => {
          const { access_token } = response.data;
          console.log("response.data: " + JSON.stringify(response.data));
          console.log("access_token: " + access_token);

          axios.get('https://www.strava.com/api/v3/athlete', {
            headers: { Authorization: `Bearer ${access_token}` },
          }).then(userResponse => {
            setIsAuthenticated(true);
            console.log(JSON.stringify(userResponse.data));

            const city = userResponse.data.city
            const state = userResponse.data.state
            const formattedLocation = `${city}, ${state}`;
            // send the access_token and user id to the backend
            axios.post('http://127.0.0.1:5000/recommendations', {
              id: userResponse.data.id,
              location: formattedLocation
            }, {
              headers: { Authorization: `Bearer ${access_token}` }
            })
            .then(recommendationsResponse => {
              console.log("Recommendations on frontend:", recommendationsResponse.data);
              setRecommendationData(recommendationsResponse.data['recommendations']);
            })
            .catch(error => {
              console.error('Error fetching recommendations:', error);
              setIsLoading(false);
            })
            .finally(() => {
              setIsLoading(false); // Set loading state to false after fetching recommendations
            });
          }).catch(error => {
            console.error('Error fetching athlete data:', error);
            setIsLoading(false);
          });

        }).catch(error => {
          console.error('Error fetching access token:', error);
          setIsAuthenticated(false);
          setIsLoading(false);
          hasFetchedToken.current = false; // Reset ref if there's an error
        });
    }
  }, []);

  const handleLogin = () => {
    try {
      // Redirect to Strava's OAuth authorization page
      const responseType = 'code';
      const scope = 'read';
      console.log("about to login");
      const authUrl = `https://www.strava.com/oauth/authorize?client_id=${process.env.NEXT_PUBLIC_STRAVA_CLIENT_ID}&response_type=${responseType}&redirect_uri=${process.env.NEXT_PUBLIC_STRAVA_REDIRECT_URI}&scope=${scope},activity:read_all,profile:read_all`;
      console.log("Redirecting to: ", authUrl);
      router.push(authUrl);
      // window.location.href = authUrl;
    } catch (error) {
      console.error('An error occurred during login: ', error)
    }
  };

  return (
    <div className={`flex flex-col w-64 bg-gray-800 text-white p-4 transition-transform duration-300 ease-in-out ${isOpen ? 'block' : 'hidden'}`}>
      <button onClick={toggleSidebar} className="text-green-200 hover:text-white mb-4">
        {isOpen ? 'Close' : 'Open'}
      </button>
      {!isAuthenticated ? (
        <div className='flex-grow'>
          <p>Please log in to Strava to see your recommendations.</p>
          <button onClick={handleLogin} className="hover:bg-green-700 rounded">
            <Image src="/strava/connect-with-strava.svg" alt="Connect with Strava" width={193} height={48} />
          </button>
        </div>
      ) : (
        <div className="flex-grow mt-4 overflow-y-auto">          
          {isLoading ? ( // Render loading message while recommendations are being fetched
            <p>Loading...</p>
          ) : (
            recommendationData && recommendationData.length > 0 ? (
              recommendationData.map((reco, index) => (
                <RecommendationCard
                  key={index}
                  date={reco["Race Date"]}
                  name={reco["Race Name"]}
                  distances={reco["Distances Available"]}
                  location={reco["Location"]}
                  details={reco["Race Info"]}
                />
              ))
            ) : (
              <p>No recommendations available.</p>
            )
          )}
        </div>
      )}
      <div className='mt-auto'>
        <Image src="/strava/powered-by-strava.svg" alt="Powered by Strava" width={193} height={48} />
      </div>
    </div>
  );
};

export default Sidebar;