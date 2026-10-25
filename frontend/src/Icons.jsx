/* eslint-disable react-refresh/only-export-components */
const p = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', viewBox: '0 0 24 24' }
const I = (d) => (props) => <svg {...p} {...props}>{d}</svg>
export const Home = I(<><path d="M3 11l9-8 9 8" /><path d="M5 10v10h14V10" /></>)
export const Cart = I(<><circle cx="9" cy="20" r="1.4" /><circle cx="18" cy="20" r="1.4" /><path d="M2 3h3l2.6 12h11l2-8H6" /></>)
export const Box = I(<><path d="M21 8l-9-5-9 5v8l9 5 9-5z" /><path d="M3 8l9 5 9-5M12 13v8" /></>)
export const Tag = I(<><path d="M3 12V3h9l9 9-9 9z" /><circle cx="7.5" cy="7.5" r="1.3" /></>)
export const Truck = I(<><path d="M1 6h13v10H1zM14 10h5l4 4v2h-9" /><circle cx="6" cy="18" r="2" /><circle cx="18" cy="18" r="2" /></>)
export const Users = I(<><circle cx="9" cy="8" r="3.5" /><path d="M2 21c0-4 3-6 7-6s7 2 7 6" /><path d="M17 4.5a3.5 3.5 0 010 7M22 21c0-3-1.5-5-4-5.8" /></>)
export const Bag = I(<><path d="M5 7h14l-1 14H6z" /><path d="M9 7a3 3 0 016 0" /></>)
export const Wallet = I(<><path d="M3 7h17a1 1 0 011 1v11a1 1 0 01-1 1H4a1 1 0 01-1-1z" /><path d="M3 7l12-4v4M17 14h2" /></>)
export const Trend = I(<><path d="M3 17l6-6 4 4 8-9" /><path d="M15 6h6v6" /></>)
export const Receipt = I(<><path d="M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2z" /><path d="M9 8h6M9 12h6" /></>)
export const Alert = I(<><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18h.01" /></>)
export const Menu = I(<><path d="M4 6h16M4 12h16M4 18h16" /></>)
