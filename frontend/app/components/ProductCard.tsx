'use client';

import React from 'react';

interface Product {
  product_id: string;
  name: string;
  category: string;
  description: string;
  top_ingredients: string;
  tags: string;
  'price (USD)': number;
  'margin (%)': number;
}

interface ProductCardProps {
  product: Product;
}

export default function ProductCard({ product }: ProductCardProps) {
  // Split tags and format them properly
  const tags = product.tags
    .split('|')  // Split by pipe character
    .map(tag => tag.trim())
    .filter(tag => tag.length > 0);  // Remove empty tags
  
  // Format ingredients with proper spacing
  const ingredients = product.top_ingredients.split(';').map(ing => ing.trim());

  // Format price safely
  const formatPrice = (price: any) => {
    console.log('Raw price value:', price, 'Type:', typeof price);
    
    if (price === null || price === undefined || isNaN(price)) {
      console.log('Price is invalid:', price);
      return 'Price not available';
    }
    
    const formattedPrice = `$${Number(price).toFixed(2)}`;
    console.log('Formatted price:', formattedPrice);
    return formattedPrice;
  };

  return (
    <div className="group bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 border border-gray-100">
      <div className="p-5">
        {/* Header with Category Badge */}
        <div className="flex justify-between items-start mb-3">
          <h3 className="text-lg font-semibold text-gray-800 group-hover:text-blue-600 transition-colors duration-200 line-clamp-2">
            {product.name}
          </h3>
          <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100 ml-2 flex-shrink-0">
            {product.category}
          </span>
        </div>
        
        {/* Description */}
        <p className="text-gray-600 mb-4 text-sm leading-relaxed line-clamp-2">
          {product.description}
        </p>
        
        {/* Ingredients Section */}
        <div className="mb-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-3 border border-blue-100/50">
          <h4 className="text-xs font-semibold text-blue-800 mb-2 uppercase tracking-wider">
            Key Ingredients
          </h4>
          <ul className="text-sm text-gray-700 space-y-1">
            {ingredients.map((ingredient, index) => (
              <li key={index} className="flex items-center">
                <span className="w-1 h-1 bg-blue-400 rounded-full mr-2"></span>
                {ingredient}
              </li>
            ))}
          </ul>
        </div>
        
        {/* Tags Section */}
        <div className="mb-4">
          <h4 className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wider">
            Tags
          </h4>
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border border-blue-100 hover:from-blue-100 hover:to-indigo-100 transition-colors duration-200"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
        
        {/* Price and Add to Cart */}
        <div className="flex justify-between items-center pt-3 border-t border-gray-100">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-gray-900">{formatPrice(product['price (USD)'])}</span>
            <span className="text-xs text-gray-500 bg-gray-50 px-2 py-0.5 rounded-full border border-gray-200">Free Shipping</span>
          </div>
          <button className="px-3 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm rounded-lg hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200 transform hover:scale-105 shadow-sm">
            Add to Cart
          </button>
        </div>
      </div>
    </div>
  );
} 