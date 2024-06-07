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
    <div className="max-w-sm rounded-lg overflow-hidden shadow-lg px-4 py-2 mb-4 bg-gray-700">
      <div className="text-red-700 text-xl mb-2">{name}</div>
      <p className="text-white text-base">{date}</p>
      <p className="text-white text-base">Location: {location}</p>
      <p className="text-white text-base">Distances: {distances}</p>
      <a href={details} className="text-blue-500 hover:underline">Details</a>
    </div>
  );
};

export default RecommendationCard;