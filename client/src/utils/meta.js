// Utility functions for dynamic meta tag updates

export const updateMetaTags = (videoData) => {
  if (!videoData) return;

  const title = videoData.title || 'YouTube';
  const description = videoData.description ? 
    videoData.description.substring(0, 160) + '...' : 
    '動画共有サイト - 日本のトレンド動画やおすすめコンテンツを視聴できます。';
  const thumbnail = videoData.videoThumbnails?.[0]?.url || '@assets/7985007a_1755031665661.avif';
  const author = videoData.author || 'YouTube';
  const url = `${window.location.origin}/watch/${videoData.videoId}`;

  // Update document title
  document.title = `${title} - YouTube`;

  // Update meta description
  updateMetaTag('name', 'description', description);

  // Update Open Graph tags
  updateMetaTag('property', 'og:title', title);
  updateMetaTag('property', 'og:description', description);
  updateMetaTag('property', 'og:image', thumbnail);
  updateMetaTag('property', 'og:url', url);
  updateMetaTag('property', 'og:type', 'video.other');

  // Update Twitter Card tags
  updateMetaTag('property', 'twitter:title', title);
  updateMetaTag('property', 'twitter:description', description);
  updateMetaTag('property', 'twitter:image', thumbnail);
  updateMetaTag('property', 'twitter:url', url);
  updateMetaTag('property', 'twitter:card', 'summary_large_image');

  // Add video-specific meta tags
  if (videoData.lengthSeconds) {
    updateMetaTag('property', 'video:duration', videoData.lengthSeconds);
  }
  if (author) {
    updateMetaTag('property', 'video:director', author);
  }
  updateMetaTag('property', 'video:tag', 'YouTube, 動画, 学習, エンターテイメント');
};

export const resetMetaTags = () => {
  document.title = 'YouTube';
  
  const defaultDescription = '動画共有サイト - 日本のトレンド動画やおすすめコンテンツを視聴できます。';
  const defaultImage = '@assets/7985007a_1755031665661.avif';
  const defaultUrl = window.location.origin;

  updateMetaTag('name', 'description', defaultDescription);
  updateMetaTag('property', 'og:title', 'YouTube');
  updateMetaTag('property', 'og:description', defaultDescription);
  updateMetaTag('property', 'og:image', defaultImage);
  updateMetaTag('property', 'og:url', defaultUrl);
  updateMetaTag('property', 'og:type', 'website');
  updateMetaTag('property', 'twitter:title', 'YouTube');
  updateMetaTag('property', 'twitter:description', defaultDescription);
  updateMetaTag('property', 'twitter:image', defaultImage);
  updateMetaTag('property', 'twitter:url', defaultUrl);
};

const updateMetaTag = (attribute, attributeValue, content) => {
  let element = document.querySelector(`meta[${attribute}="${attributeValue}"]`);
  
  if (!element) {
    element = document.createElement('meta');
    element.setAttribute(attribute, attributeValue);
    document.head.appendChild(element);
  }
  
  element.setAttribute('content', content);
};

// Generate structured data for video
export const generateVideoStructuredData = (videoData) => {
  if (!videoData) return;

  const structuredData = {
    "@context": "https://schema.org",
    "@type": "VideoObject",
    "name": videoData.title,
    "description": videoData.description || '',
    "thumbnailUrl": videoData.videoThumbnails?.[0]?.url || '',
    "uploadDate": videoData.publishedText || new Date().toISOString(),
    "duration": videoData.lengthSeconds ? `PT${videoData.lengthSeconds}S` : undefined,
    "author": {
      "@type": "Person", 
      "name": videoData.author || 'Unknown'
    },
    "publisher": {
      "@type": "Organization",
      "name": "YouTube",
      "logo": {
        "@type": "ImageObject",
        "url": "@assets/7985007a_1755031665661.avif"
      }
    },
    "embedUrl": `${window.location.origin}/watch/${videoData.videoId}`,
    "interactionStatistic": videoData.viewCount ? {
      "@type": "InteractionCounter",
      "interactionType": { "@type": "WatchAction" },
      "userInteractionCount": videoData.viewCount
    } : undefined
  };

  // Remove undefined fields
  Object.keys(structuredData).forEach(key => 
    structuredData[key] === undefined && delete structuredData[key]
  );

  // Update or create structured data script
  let script = document.querySelector('script[type="application/ld+json"]');
  if (!script) {
    script = document.createElement('script');
    script.type = 'application/ld+json';
    document.head.appendChild(script);
  }
  
  script.textContent = JSON.stringify(structuredData);
};