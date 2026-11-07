declare module 'papaparse' {
  export function parse(input: string, config?: any): any;
  const Papa: {
    parse: typeof parse;
  };
  export default Papa;
}
