import React from 'react';

type CardProps = {
  date: string,
  name: string,
  distances: string,
  location: string,
  details: string
}

const RecommendationCard: React.FC<CardProps> = ({ date, name, distances, location, details }) => {
  return (
    <div className="max-w-md rounded-lg overflow-hidden shadow-lg px-6 py-4 mb-6 bg-white border border-gray-200">
      <div className="text-gray-800 text-xl font-extrabold mb-2">{name}</div>
      <p className="text-gray-600 text-sm mb-2 font-semibold">{date}</p>
      <p className="text-gray-600 text-sm mb-2"><span className='font-bold'>Location:</span> {location}</p>
      <p className="text-gray-600 text-sm mb-4"><span className='font-bold'>Distances:</span> {distances}</p>
      <a href={details} className="text-blue-600 hover:underline">Details</a>
    </div>
  );
};

export default RecommendationCard;