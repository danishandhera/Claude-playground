/* ─── CAREGIVERS ──────────────────────────────────────────────────────────── */
// Mock caregiver directory. Served to the app via useCaregivers() in ./hooks.js.
export const CAREGIVERS = [
  {
    id:1, name:"Shanthi Krishnamurthy", initials:"SK", hue:"#6B8F71",
    tagline:"Ayurvedic sutika specialist, 14 years",
    city:"Dubai", district:"Bur Dubai & Old Dubai", area:"Al Karama",
    traditions:["south-indian"], rate:3200, availDays:18,
    exp:14, rating:4.9, reviews:38, liveIn:false,
    langs:["Tamil","Malayalam","English"],
    certs:["Ayurvedic Postnatal Care (Kerala)","Infant Massage Therapist"],
    sources:["Mama Tribe UAE Facebook","The National expat feature"],
    verified:true,
    review:{ by:"Priya M.", when:"March 2026", stars:5,
      text:"Shanthi understood everything without me explaining once. Abhyanga massages were transformative — I felt my body healing daily. She prepared all the Sutika foods perfectly and guided our Namakarana ceremony beautifully." }
  },
  {
    id:2, name:"Nazia Hussain", initials:"NH", hue:"#7A6352",
    tagline:"Pakistani dhai maa tradition, 9 years",
    city:"Dubai", district:"Deira & Creekside", area:"Deira",
    traditions:["pakistani","north-indian"], rate:2800, availDays:12,
    exp:9, rating:4.8, reviews:22, liveIn:true,
    langs:["Urdu","Punjabi","Hindi","Arabic","English"],
    certs:["Postnatal Nutrition (Pakistan)","Baby Care & Swaddling"],
    sources:["Dubai Mums Meet Facebook","Mama Hub UAE"],
    verified:true,
    review:{ by:"Fatima A.", when:"Feb 2026", stars:5,
      text:"Nazia was like having a knowledgeable dadi at home. Her panjiri matched my mother's recipe exactly. The Aqiqah arrangements were handled perfectly. She managed my 3-year-old so I got real rest." }
  },
  {
    id:3, name:"Ji-Young Park", initials:"JY", hue:"#4A7A9B",
    tagline:"Certified sanhujorisa, Korean tradition",
    city:"Abu Dhabi", district:"Abu Dhabi Island", area:"Al Khalidiyah",
    traditions:["korean"], rate:4100, availDays:35,
    exp:6, rating:5.0, reviews:11, liveIn:true,
    langs:["Korean","English"],
    certs:["Certified Sanhujorisa (Seoul)","Korean Postpartum Nutrition"],
    sources:["Korean Expats UAE Facebook","Eklektik Mama community"],
    verified:true,
    review:{ by:"Soo-Jin L.", when:"Jan 2026", stars:5,
      text:"Ji-Young is a true sanhujorisa. Her miyeokguk was perfect every morning. I slept 6-hour stretches because she handled everything overnight. My joints healed beautifully — she enforced the warmth protocol without compromise." }
  },
  {
    id:4, name:"Fatimah binti Yusof", initials:"FY", hue:"#1A7A6E",
    tagline:"Berpantang specialist, 11 years",
    city:"Sharjah & Northern Emirates", district:"Sharjah City", area:"Al Majaz",
    traditions:["malay"], rate:2500, availDays:8,
    exp:11, rating:4.7, reviews:29, liveIn:true,
    langs:["Malay","Arabic","English"],
    certs:["Traditional Malay Postnatal Care","Urut Massage Certified"],
    sources:["Malay Community UAE Facebook","Muslim Mothers Dubai group"],
    verified:true,
    review:{ by:"Aisha R.", when:"March 2026", stars:5,
      text:"Fatimah's bengkung binding changed my recovery. My tummy was nearly flat by week 4. Fresh jamu every morning. She handled all our berpantang rules without a single explanation needed." }
  },
  {
    id:5, name:"Malee Suthiporn", initials:"MS", hue:"#7B5EA7",
    tagline:"Certified Yu Fai practitioner, Thai tradition",
    city:"Dubai", district:"Jumeirah & Coast", area:"Umm Suqeim",
    traditions:["thai"], rate:3500, availDays:60,
    exp:8, rating:4.9, reviews:17, liveIn:false,
    langs:["Thai","English"],
    certs:["Certified Yu-Fai Practitioner","Thai Herbal Medicine"],
    sources:["Thai Community Dubai Facebook","Mama Hub UAE"],
    verified:true,
    review:{ by:"Nong T.", when:"Feb 2026", stars:5,
      text:"Malee is the real thing. My recovery after a difficult birth was so much faster than my first. The yu fai sessions were gentle but incredibly effective. She arranged the monk visit seamlessly." }
  },
  {
    id:6, name:"Rekha Shetty", initials:"RS", hue:"#5C7A3E",
    tagline:"South & North Indian care, 17 years",
    city:"Dubai", district:"Dubai Marina & West", area:"Al Barsha",
    traditions:["south-indian","north-indian"], rate:2900, availDays:10,
    exp:17, rating:4.9, reviews:54, liveIn:false,
    langs:["Kannada","Hindi","English","Tamil"],
    certs:["Ayurvedic Postnatal Care","Infant & Maternal Massage","Lactation Support"],
    sources:["South Indian Community Dubai","Dubai Mums Facebook group"],
    verified:true,
    review:{ by:"Deepa K.", when:"April 2026", stars:5,
      text:"17 years shows in everything Rekha does. She managed our Namkaran perfectly. Sesame oil massages reduced my back pain within days. Methi ladoo, rasam, khichdi — all perfect. Truly irreplaceable." }
  },
];
