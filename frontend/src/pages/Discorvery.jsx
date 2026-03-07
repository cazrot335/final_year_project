import { useState, useEffect } from "react";
import { Card, Input, Button, Row, Col, Pagination, Spin } from "antd";
import "../styles/discovery.css";
import ProfileCard from "../components/ProfileCard";
export default function Discovery() {

  const [designationFilter,setDesignationFilter] = useState("");
const [locationFilter,setLocationFilter] = useState("");

  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [pages, setPages] = useState(1);

  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(false);

  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const limit = 6;


 const fetchProfiles = (pageNum = 1) => {

 fetch(`http://localhost:5000/api/profiles?page=${pageNum}&limit=6&designation=${designationFilter}&location=${locationFilter}`)
   .then(res => res.json())
   .then(data => {

     setProfiles(data.results);
     setTotal(data.total_profiles);

   });

};


  useEffect(() => {
    fetchProfiles();
  }, []);


  const runDiscovery = async () => {

    setLoading(true);

    try {

      await fetch(
        `http://localhost:5000/scrape-linkedin?keyword=${keyword}&location=${location}&pages=${pages}`
      );

      setTimeout(() => {
        fetchProfiles(1);
        setLoading(false);
      }, 1200);

    } catch (err) {
      console.error(err);
      setLoading(false);
    }

  };


  return (

    <div className="discovery-container">

      {/* SEARCH LAYER */}

      <div className="search-layer">

        <Input
          placeholder="Job title (Python Developer)"
          value={keyword}
          onChange={(e)=>setKeyword(e.target.value)}
        />

        <Input
          placeholder="Location"
          value={location}
          onChange={(e)=>setLocation(e.target.value)}
        />

        <Input
          type="number"
          placeholder="Pages"
          value={pages}
          onChange={(e)=>setPages(e.target.value)}
        />

        <Button
          type="primary"
          onClick={runDiscovery}
        >
          Discover Talent
        </Button>

        <div className="filter-layer">

  <Input
    placeholder="Filter by designation"
    value={designationFilter}
    onChange={(e)=>setDesignationFilter(e.target.value)}
  />

  <Input
    placeholder="Filter by location"
    value={locationFilter}
    onChange={(e)=>setLocationFilter(e.target.value)}
  />

  <Button
    onClick={()=>fetchProfiles(1)}
  >
    Apply Filters
  </Button>

</div>

      </div>


      {/* LOADER */}

      {loading && (
        <div className="loader">
          <Spin size="large" />
          <p>Running talent discovery pipeline...</p>
        </div>
      )}


      {/* CARD GRID */}

    <Row gutter={[16,16]}>

  {profiles.map(profile => (

    <Col span={8} key={profile.id}>

      <ProfileCard profile={profile} />

    </Col>

  ))}

</Row>


      {/* PAGINATION */}

      <div className="pagination">

        <Pagination
          current={page}
          pageSize={limit}
          total={total}
          onChange={(p)=>{

            setPage(p);
            fetchProfiles(p);

          }}
        />

      </div>

    </div>

  );

}